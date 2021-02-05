from typing import Dict, Generator, List, Optional

import bs4
import feedparser
from pydantic import ValidationError

from .date_parser import parse_date
from .models import Audio, Feed, Item


def parse_xml(xml: bytes) -> Feed:
    result = feedparser.parse(xml)
    channel = result["feed"]

    return Feed(
        title=channel.get("title", None),
        description=channel.get("description", ""),
        link=channel.get("link", ""),
        explicit=bool(channel.get("itunes_explicit", False)),
        image=parse_image(xml, channel),
        authors=list(parse_authors(channel.get("authors", []))),
        categories=list(parse_tags(channel.get("tags", []))),
        items=list(parse_items(result)),
    )


def parse_items(result: Dict) -> Generator:
    guids = set()
    for entry in result.get("entries", []):
        guid = parse_guid(entry)
        if guid and guid not in guids:
            try:
                yield Item(
                    guid=guid,
                    title=entry.get("title"),
                    duration=entry.get("itunes_duration", ""),
                    explicit=bool(entry.get("itunes_explicit", False)),
                    audio=parse_audio(entry),
                    description=parse_description(entry),
                    keywords=" ".join(parse_tags(entry.get("tags", []))),
                    pub_date=parse_date(entry.get("published")),
                )
                guids.add(guid)
            except ValidationError:
                pass


def parse_guid(entry: Dict) -> Optional[str]:
    for key in ("id", "itunes_episode"):
        if key in entry and (value := entry[key]):
            return value
    return None


def parse_tags(tags: List[Dict]) -> Generator:
    for t in tags:
        if term := t.get("term"):
            yield term


def parse_authors(authors: List[Dict]) -> Generator:
    for a in authors:
        if name := a.get("name"):
            yield name


def parse_audio(entry: Dict) -> Optional[Audio]:

    for link in entry.get("links", []):
        try:
            return Audio(
                rel=link["rel"],
                type=link["type"],
                url=link["url"],
                length=link.get("length", None),
            )
        except (ValidationError, KeyError):
            pass

    return None


def parse_description(entry: Dict) -> str:
    try:
        return (
            [
                c["value"]
                for c in entry.get("content", [])
                if c.get("type") == "text/html"
            ]
            + [
                entry[field]
                for field in ("description", "summary", "subtitle")
                if field in entry and entry[field]
            ]
        )[0]
    except (KeyError, IndexError):
        return ""


def parse_image(xml: bytes, channel: Dict) -> Optional[str]:
    # try itunes image first
    soup = bs4.BeautifulSoup(xml, "lxml")
    tag = soup.find("itunes:image")
    if tag and "href" in tag.attrs:
        return tag.attrs["href"]

    try:
        return channel["image"]["href"]
    except KeyError:
        pass

    return None
