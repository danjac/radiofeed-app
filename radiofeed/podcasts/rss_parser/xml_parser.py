import logging
from typing import Dict, List, Optional

import bs4
import feedparser
from pydantic import ValidationError

from .date_parser import parse_date
from .models import Audio, Feed, Item

logger = logging.getLogger(__name__)


def parse_xml(xml: bytes) -> Optional[Feed]:
    result = feedparser.parse(xml)
    channel = result["feed"]

    try:
        return Feed(
            title=channel.get("title", None),
            description=channel.get("description", ""),
            link=channel.get("link", None),
            explicit=bool(channel.get("itunes_explicit", False)),
            authors=[a["name"] for a in channel.get("authors", []) if "name" in a],
            categories=parse_tags(channel.get("tags", [])),
            image=parse_image(xml, channel),
            items=parse_items(result),
        )
    except ValidationError as e:
        logger.error(str(e))
        return None


def parse_items(result: Dict) -> List[Item]:
    entries = list(
        {e["id"]: e for e in result.get("entries", []) if "id" in e}.values()
    )
    return [entry for entry in [parse_item(entry) for entry in entries] if entry]


def parse_item(entry: Dict) -> Optional[Item]:

    try:
        return Item(
            guid=entry["id"],
            title=entry.get("title"),
            duration=entry.get("itunes_duration", ""),
            explicit=bool(entry.get("itunes_explicit", False)),
            audio=parse_audio(entry),
            description=parse_description(entry),
            keywords=" ".join(parse_tags(entry.get("tags", []))),
            pub_date=parse_date(entry.get("published")),
        )
    except ValidationError:
        return None


def parse_tags(tags: List[Dict]) -> List[str]:
    return [t["term"] for t in tags if "term" in t]


def parse_audio(entry: Dict) -> Optional[Audio]:

    try:
        audio = [
            link
            for link in entry.get("links", [])
            if link.get("rel") == "enclosure"
            and link.get("type", "").startswith("audio/")
        ][0]
        url = audio["url"]
        type = audio["type"]
    except (IndexError, KeyError):
        return None

    length: Optional[int]

    try:
        length = int(audio["length"])
    except (KeyError, ValueError):
        length = None

    return Audio(url=url, type=type, length=length)


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
