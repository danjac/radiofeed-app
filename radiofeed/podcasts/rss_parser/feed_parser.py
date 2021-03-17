from typing import Generator, List, Optional

import lxml

from lxml.etree import ElementBase
from pydantic import ValidationError

from .models import Audio, Feed, Item

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "googleplay": "http://www.google.com/schemas/play-podcasts/1.0",
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "media": "http://search.yahoo.com/mrss/",
    "podcast": "https://podcastindex.org/namespace/1.0",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
}


def parse_feed(raw: bytes) -> Feed:
    rss = lxml.etree.fromstring(raw, parser=lxml.etree.XMLParser(strip_cdata=False))
    channel = rss.find("channel")

    if channel is None:
        raise ValueError("Not a valid RSS feed")

    return Feed(
        title=parse_text(channel, "title"),
        link=parse_text(channel, "link"),
        categories=parse_attribute_list(channel, ".//itunes:category", "text"),
        authors=set(parse_channel_authors(channel)),
        image=parse_channel_image(channel),
        description=parse_channel_description(channel),
        explicit=parse_explicit(channel),
        items=list(parse_rss_items(channel)),
    )


def parse_tag(parent: ElementBase, xpath: str) -> Optional[ElementBase]:
    return parent.find(xpath, NAMESPACES)


def parse_tags(parent: ElementBase, xpath: str) -> List[ElementBase]:
    return parent.findall(xpath, NAMESPACES)


def parse_attribute(parent: ElementBase, xpath: str, attr: str) -> Optional[str]:
    if (tag := parse_tag(parent, xpath)) is None:
        return None
    try:
        return tag.attrib[attr]
    except KeyError:
        return None


def parse_attribute_list(parent: ElementBase, xpath: str, attr: str) -> List[str]:
    return [
        (tag.attrib[attr] or "")
        for tag in parse_tags(parent, xpath)
        if attr in tag.attrib
    ]


def parse_text(parent: ElementBase, xpath: str) -> str:
    if (tag := parse_tag(parent, xpath)) is None:
        return ""
    return tag.text or ""


def parse_text_list(parent: ElementBase, xpath: str) -> List[str]:
    return [(item.text or "") for item in parse_tags(parent, xpath)]


def parse_explicit(parent: ElementBase) -> bool:
    return parse_text(parent, "itunes:explicit").lower() == "yes"


def parse_rss_items(channel: ElementBase) -> Generator:

    guids = set()
    for item in parse_tags(channel, "item"):
        guid = parse_text(item, "guid") or parse_text(item, "itunes:episode")

        if guid and guid not in guids:
            try:
                yield Item(
                    guid=guid,
                    title=parse_text(item, "title"),
                    duration=parse_text(item, "itunes:duration"),
                    link=parse_text(item, "link"),
                    pub_date=parse_text(item, "pubDate"),
                    explicit=parse_explicit(item),
                    audio=parse_audio(item),
                    description=parse_item_description(item),
                    keywords=parse_item_keywords(item),
                )
                guids.add(guid)
            except ValidationError:
                pass


def parse_audio(item: ElementBase) -> Optional[Audio]:

    if (enclosure := parse_tag(item, "enclosure")) is None:
        return None

    return Audio(
        length=enclosure.attrib.get("length"),
        url=enclosure.attrib.get("url"),
        type=enclosure.attrib.get("type"),
    )


def parse_channel_image(channel: ElementBase) -> Optional[str]:
    return (
        parse_attribute(channel, "itunes:image", "href")
        or parse_text(channel, "image/url")
        or parse_attribute(channel, "googleplay:image", "href")
    )


def parse_channel_description(channel: ElementBase) -> str:
    return (
        parse_text(channel, "description")
        or parse_text(channel, "googleplay:description")
        or parse_text(channel, "itunes:summary")
        or parse_text(channel, "itunes:subtitle")
    )


def parse_channel_authors(channel: ElementBase) -> List[str]:
    return parse_text_list(channel, "itunes:owner/itunes:name") + parse_text_list(
        channel, "itunes:author"
    )


def parse_item_description(item: ElementBase) -> str:

    return (
        parse_text(item, "content:encoded")
        or parse_text(item, "description")
        or parse_text(item, "googleplay:description")
        or parse_text(item, "itunes:summary")
        or parse_text(item, "itunes:subtitle")
    )


def parse_item_keywords(item: ElementBase) -> str:
    rv = parse_text_list(item, "category")
    if (keywords := parse_text(item, "itunes:keywords")) :
        rv.append(keywords)
    return " ".join(rv)
