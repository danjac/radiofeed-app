# Standard Library
import io
import mimetypes
import os
import random
import uuid
from functools import lru_cache
from urllib.parse import urlparse

# Django
from django.core.files.images import ImageFile
from django.utils import timezone
from django.utils.timezone import is_aware, make_aware

# Third Party Libraries
import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

# RadioFeed
from radiofeed.episodes.models import Episode

# Local
from .models import Category

TZ_INFOS = {
    k: v * 3600
    for k, v in (
        ("A", 1),
        ("ACDT", 10.5),
        ("ACST", 9.5),
        ("ACT", -5),
        ("ACWST", 8.75),
        ("ADT", 4),
        ("AEDT", 11),
        ("AEST", 10),
        ("AET", 10),
        ("AFT", 4.5),
        ("AKDT", -8),
        ("AKST", -9),
        ("ALMT", 6),
        ("AMST", -3),
        ("AMT", -4),
        ("ANAST", 12),
        ("ANAT", 12),
        ("AQTT", 5),
        ("ART", -3),
        ("AST", 3),
        ("AT", -4),
        ("AWDT", 9),
        ("AWST", 8),
        ("AZOST", 0),
        ("AZOT", -1),
        ("AZST", 5),
        ("AZT", 4),
        ("AoE", -12),
        ("B", 2),
        ("BNT", 8),
        ("BOT", -4),
        ("BRST", -2),
        ("BRT", -3),
        ("BST", 6),
        ("BTT", 6),
        ("C", 3),
        ("CAST", 8),
        ("CAT", 2),
        ("CCT", 6.5),
        ("CDT", -5),
        ("CEST", 2),
        ("CET", 1),
        ("CHADT", 13.75),
        ("CHAST", 12.75),
        ("CHOST", 9),
        ("CHOT", 8),
        ("CHUT", 10),
        ("CIDST", -4),
        ("CIST", -5),
        ("CKT", -10),
        ("CLST", -3),
        ("CLT", -4),
        ("COT", -5),
        ("CST", -6),
        ("CT", -6),
        ("CVT", -1),
        ("CXT", 7),
        ("ChST", 10),
        ("D", 4),
        ("DAVT", 7),
        ("DDUT", 10),
        ("E", 5),
        ("EASST", -5),
        ("EAST", -6),
        ("EAT", 3),
        ("ECT", -5),
        ("EDT", -4),
        ("EEST", 3),
        ("EET", 2),
        ("EGST", 0),
        ("EGT", -1),
        ("EST", -5),
        ("ET", -5),
        ("F", 6),
        ("FET", 3),
        ("FJST", 13),
        ("FJT", 12),
        ("FKST", -3),
        ("FKT", -4),
        ("FNT", -2),
        ("G", 7),
        ("GALT", -6),
        ("GAMT", -9),
        ("GET", 4),
        ("GFT", -3),
        ("GILT", 12),
        ("GMT", 0),
        ("GST", 4),
        ("GYT", -4),
        ("H", 8),
        ("HDT", -9),
        ("HKT", 8),
        ("HOVST", 8),
        ("HOVT", 7),
        ("HST", -10),
        ("I", 9),
        ("ICT", 7),
        ("IDT", 3),
        ("IOT", 6),
        ("IRDT", 4.5),
        ("IRKST", 9),
        ("IRKT", 8),
        ("IRST", 3.5),
        ("IST", 5.5),
        ("JST", 9),
        ("K", 10),
        ("KGT", 6),
        ("KOST", 11),
        ("KRAST", 8),
        ("KRAT", 7),
        ("KST", 9),
        ("KUYT", 4),
        ("L", 11),
        ("LHDT", 11),
        ("LHST", 10.5),
        ("LINT", 14),
        ("M", 12),
        ("MAGST", 12),
        ("MAGT", 11),
        ("MART", 9.5),
        ("MAWT", 5),
        ("MDT", -6),
        ("MHT", 12),
        ("MMT", 6.5),
        ("MSD", 4),
        ("MSK", 3),
        ("MST", -7),
        ("MT", -7),
        ("MUT", 4),
        ("MVT", 5),
        ("MYT", 8),
        ("N", -1),
        ("NCT", 11),
        ("NDT", 2.5),
        ("NFT", 11),
        ("NOVST", 7),
        ("NOVT", 7),
        ("NPT", 5.5),
        ("NRT", 12),
        ("NST", 3.5),
        ("NUT", -11),
        ("NZDT", 13),
        ("NZST", 12),
        ("O", -2),
        ("OMSST", 7),
        ("OMST", 6),
        ("ORAT", 5),
        ("P", -3),
        ("PDT", -7),
        ("PET", -5),
        ("PETST", 12),
        ("PETT", 12),
        ("PGT", 10),
        ("PHOT", 13),
        ("PHT", 8),
        ("PKT", 5),
        ("PMDT", -2),
        ("PMST", -3),
        ("PONT", 11),
        ("PST", -8),
        ("PT", -8),
        ("PWT", 9),
        ("PYST", -3),
        ("PYT", -4),
        ("Q", -4),
        ("QYZT", 6),
        ("R", -5),
        ("RET", 4),
        ("ROTT", -3),
        ("S", -6),
        ("SAKT", 11),
        ("SAMT", 4),
        ("SAST", 2),
        ("SBT", 11),
        ("SCT", 4),
        ("SGT", 8),
        ("SRET", 11),
        ("SRT", -3),
        ("SST", -11),
        ("SYOT", 3),
        ("T", -7),
        ("TAHT", -10),
        ("TFT", 5),
        ("TJT", 5),
        ("TKT", 13),
        ("TLT", 9),
        ("TMT", 5),
        ("TOST", 14),
        ("TOT", 13),
        ("TRT", 3),
        ("TVT", 12),
        ("U", -8),
        ("ULAST", 9),
        ("ULAT", 8),
        ("UTC", 0),
        ("UYST", -2),
        ("UYT", -3),
        ("UZT", 5),
        ("V", -9),
        ("VET", -4),
        ("VLAST", 11),
        ("VLAT", 10),
        ("VOST", 6),
        ("VUT", 11),
        ("W", -10),
        ("WAKT", 12),
        ("WARST", -3),
        ("WAST", 2),
        ("WAT", 1),
        ("WEST", 1),
        ("WET", 0),
        ("WFT", 12),
        ("WGST", -2),
        ("WGT", -3),
        ("WIB", 7),
        ("WIT", 9),
        ("WITA", 8),
        ("WST", 14),
        ("WT", 0),
        ("X", -11),
        ("Y", -12),
        ("YAKST", 10),
        ("YAKT", 9),
        ("YAPT", 10),
        ("YEKST", 6),
        ("YEKT", 5),
        ("Z", 0),
    )
}


USER_AGENTS = [
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/57.0.2987.110 "
        "Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/61.0.3163.79 "
        "Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) "
        "Gecko/20100101 "
        "Firefox/55.0"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/61.0.3163.91 "
        "Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/62.0.3202.89 "
        "Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/63.0.3239.108 "
        "Safari/537.36"
    ),
]


IMAGE_EXTENSIONS = (".jpg", ".png", ".jpeg")


class RssParser:
    def __init__(self, podcast):
        self.podcast = podcast

    @classmethod
    def parse_from_podcast(cls, podcast):
        return cls(podcast).parse()

    def parse(self):

        # fetch etag and last modified
        head_response = requests.head(
            self.podcast.rss, headers=get_headers(), timeout=5
        )
        head_response.raise_for_status()
        headers = head_response.headers

        # if etag hasn't changed then we can skip
        etag = headers.get("ETag")
        if etag and etag == self.podcast.etag:
            return []

        response = requests.get(
            self.podcast.rss, headers=get_headers(), stream=True, timeout=5
        )
        response.raise_for_status()

        data = feedparser.parse(response.content)

        feed = data["feed"]

        entries = {e["id"]: e for e in data.get("entries", []) if "id" in e}.values()
        if not entries:
            return []

        dates = [parse_date(e["published"]) for e in entries]
        now = timezone.now()

        if dates:
            pub_date = max([date for date in dates if date and date < now])

        do_update = (
            pub_date
            and self.podcast.last_updated is None
            or self.podcast.last_updated < pub_date
        )

        if not do_update:
            return []

        if etag:
            self.podcast.etag = etag

        self.podcast.title = feed["title"]
        self.podcast.description = feed["description"]
        self.podcast.language = feed.get("language", "en")[:2].strip().lower()
        self.podcast.explicit = bool(feed.get("itunes_explicit", False))

        if not self.podcast.cover_image:
            image_url = None

            # try itunes image first
            soup = BeautifulSoup(response.content, "lxml")
            itunes_img_tag = soup.find("itunes:image")
            if itunes_img_tag and "href" in itunes_img_tag.attrs:
                image_url = itunes_img_tag.attrs["href"]

            if not image_url:
                try:
                    image_url = feed["image"]["href"]
                except KeyError:
                    pass

            if image_url and (img := fetch_image_from_url(image_url)):
                self.podcast.cover_image = img

        self.podcast.link = feed.get("link")

        categories_dct = get_categories_dict()

        keywords = [t["term"] for t in feed.get("tags", [])]
        categories = [categories_dct[kw] for kw in keywords if kw in categories_dct]

        self.podcast.last_updated = now
        self.podcast.pub_date = pub_date

        keywords = [kw for kw in keywords if kw not in categories_dct]
        self.podcast.keywords = " ".join(keywords)

        authors = set(
            [
                author["name"]
                for author in feed.get("authors", [])
                if "name" in author and author["name"]
            ]
        )

        self.podcast.authors = ", ".join(authors)

        self.podcast.save()

        self.podcast.categories.set(categories)

        new_episodes = self.create_episodes_from_feed(entries)
        if new_episodes:
            self.podcast.pub_date = max(e.pub_date for e in new_episodes)
            self.podcast.save(update_fields=["pub_date"])

        return new_episodes

    def create_episodes_from_feed(self, entries):
        """Parses new episodes from podcast feed."""
        guids = self.podcast.episode_set.values_list("guid", flat=True)
        entries = [entry for entry in entries if entry["id"] not in guids]

        episodes = [
            episode
            for episode in [self.create_episode_from_feed(entry) for entry in entries]
            if episode
        ]
        return Episode.objects.bulk_create(episodes, ignore_conflicts=True)

    def create_episode_from_feed(self, entry):
        keywords = " ".join([t["term"] for t in entry.get("tags", [])])

        try:
            enclosure = [
                link
                for link in entry.get("links", [])
                if link.get("rel") == "enclosure"
                and link.get("type", "").startswith("audio/")
            ][0]
        except IndexError:
            return None

        if "url" not in enclosure or len(enclosure["url"]) > 500:
            return None

        try:
            description = (
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
        except IndexError:
            description = ""

        try:
            length = int(enclosure["length"])
        except (KeyError, ValueError):
            length = None

        pub_date = parse_date(entry["published"])
        if pub_date is None or pub_date > timezone.now():
            return

        link = entry.get("link", "")
        if len(link) > 500:
            link = None

        return Episode(
            podcast=self.podcast,
            guid=entry["id"],
            title=entry["title"],
            link=link,
            duration=entry.get("itunes_duration", ""),
            explicit=bool(entry.get("itunes_explicit", False)),
            description=description,
            keywords=keywords,
            media_url=enclosure["url"],
            media_type=enclosure["type"],
            length=length,
            pub_date=pub_date,
        )


@lru_cache
def get_categories_dict():
    return {c.name: c for c in Category.objects.all()}


def get_headers():
    """Return randomized user agent in case only browser clients allowed."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'}",
    }


def fetch_image_from_url(image_url):
    """Get an ImageFile object from a URL. Returns None if invalid/unavailable."""
    if not image_url:
        return None
    try:
        resp = requests.get(image_url, headers=get_headers())
        resp.raise_for_status()

        content_type = resp.headers["Content-Type"].split(";")[0]
        filename = get_image_filename(image_url, content_type)
        return ImageFile(io.BytesIO(resp.content), name=filename)
    except (requests.RequestException, KeyError, ValueError) as e:
        print(e)
        return None


def get_image_filename(image_url, content_type):
    """Generate a random filename with correct extension. Raises ValueError
    if invalid"""

    if not image_url:
        raise ValueError("No image_url provided")

    # check path first
    _, ext = os.path.splitext(urlparse(image_url).path)
    ext = ext.lower()
    if ext not in IMAGE_EXTENSIONS:
        ext = mimetypes.guess_extension(content_type)
    if ext not in IMAGE_EXTENSIONS:
        raise ValueError("Invalid file extension:" + image_url)
    return uuid.uuid4().hex + ext


def parse_date(value):
    try:
        dt = date_parser.parse(value, tzinfos=TZ_INFOS)
        if not is_aware(dt):
            dt = make_aware(dt)
        return dt
    except date_parser.ParserError:
        return None
