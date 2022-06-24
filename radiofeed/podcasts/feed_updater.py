from __future__ import annotations

import functools
import hashlib
import http

import attrs
import requests

from django.db import transaction
from django.utils import timezone
from django.utils.http import http_date, quote_etag

from radiofeed.episodes.models import Episode
from radiofeed.podcasts.models import Category, Podcast
from radiofeed.podcasts.parsers import date_parser, rss_parser, text_parser
from radiofeed.podcasts.utils import batcher, get_user_agent

ACCEPT_HEADER = "application/atom+xml,application/rdf+xml,application/rss+xml,application/x-netcdf,application/xml;q=0.9,text/xml;q=0.2,*/*;q=0.1"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]


class NotModified(requests.RequestException):
    ...


class DuplicateFeed(requests.RequestException):
    ...


class FeedUpdater:
    def __init__(self, podcast):
        self.podcast = podcast

    @transaction.atomic
    def update(self):
        try:
            return self.handle_success(*self.parse_rss())

        except Exception as e:
            return self.handle_failure(e)

    def handle_success(self, response, feed, content_hash):

        # taxonomy
        categories_dct = get_categories_dict()

        categories = [
            categories_dct[category]
            for category in feed.categories
            if category in categories_dct
        ]

        self.save_podcast(
            active=not feed.complete,
            content_hash=content_hash,
            rss=response.url,
            etag=response.headers.get("ETag", ""),
            http_status=response.status_code,
            modified=date_parser.parse_date(response.headers.get("Last-Modified")),
            title=feed.title,
            pub_date=feed.pub_date,
            cover_url=feed.cover_url,
            description=feed.description,
            explicit=feed.explicit,
            funding_text=feed.funding_text,
            funding_url=feed.funding_url,
            language=feed.language,
            link=feed.link,
            owner=feed.owner,
            extracted_text=self.extract_text(feed, categories),
            keywords=" ".join(
                category
                for category in feed.categories
                if category not in categories_dct
            ),
        )

        # categories
        self.podcast.categories.set(categories)  # type: ignore

        # episodes
        self.sync_episodes(feed)

        return True

    def handle_failure(self, exc):
        try:
            http_status = exc.response.status_code  # type: ignore
        except AttributeError:
            http_status = None

        match exc:
            case NotModified():
                active = True
            case requests.HTTPError():
                active = http_status not in (
                    http.HTTPStatus.FORBIDDEN,
                    http.HTTPStatus.GONE,
                    http.HTTPStatus.NOT_FOUND,
                    http.HTTPStatus.UNAUTHORIZED,
                )
            case DuplicateFeed() | rss_parser.RssParserError() | requests.RequestException():
                active = False
            case _:
                raise

        self.save_podcast(active=active, http_status=http_status)
        return False

    def save_podcast(self, **fields):
        now = timezone.now()
        Podcast.objects.filter(pk=self.podcast.id).update(
            updated=now,
            parsed=now,
            **fields,
        )

    def parse_rss(self):

        response = requests.get(
            self.podcast.rss,
            headers=self.get_feed_headers(),
            allow_redirects=True,
            timeout=10,
        )

        response.raise_for_status()

        if response.status_code == http.HTTPStatus.NOT_MODIFIED:
            raise NotModified(response=response)

        # check if another feed already has new URL
        if (
            response.url != self.podcast.rss
            and Podcast.objects.filter(rss=response.url).exists()
        ):
            raise DuplicateFeed(response=response)

        # check if content has changed (feed is not checking etag etc)
        if (
            content_hash := make_content_hash(response.content)
        ) == self.podcast.content_hash:
            raise NotModified(response=response)

        # check if another feed has exact same content
        if (
            Podcast.objects.exclude(pk=self.podcast.id).filter(
                content_hash=content_hash, active=True
            )
        ).exists():
            raise DuplicateFeed(response=response)

        return response, rss_parser.parse_rss(response.content), content_hash

    def sync_episodes(self, feed, batch_size=100):
        """Remove any episodes no longer in feed, update any current and
        add new"""

        qs = Episode.objects.filter(podcast=self.podcast)

        # remove any episodes that may have been deleted on the podcast
        qs.exclude(guid__in=[item.guid for item in feed.items]).delete()

        # determine new/current items based on presence of guid

        guids = dict(qs.values_list("guid", "pk"))

        # update existing content

        for batch in batcher(self.episodes_for_update(feed, guids), batch_size):
            Episode.fast_update_objects.fast_update(
                batch,
                fields=[
                    "cover_url",
                    "description",
                    "duration",
                    "episode",
                    "episode_type",
                    "explicit",
                    "keywords",
                    "length",
                    "media_type",
                    "media_url",
                    "pub_date",
                    "season",
                    "title",
                ],
            )

        # add new episodes

        for batch in batcher(self.episodes_for_insert(feed, guids), batch_size):
            Episode.objects.bulk_create(batch, ignore_conflicts=True)

    def episodes_for_update(self, feed, guids):

        episode_ids = set()
        for item in filter(lambda item: item.guid in guids, feed.items):
            if (episode_id := guids[item.guid]) not in episode_ids:
                yield self.make_episode(item, episode_id)
                episode_ids.add(episode_id)

    def episodes_for_insert(self, feed, guids):

        for item in filter(lambda item: item.guid not in guids, feed.items):
            yield self.make_episode(item)

    def make_episode(self, item, episode_id=None):
        return Episode(
            pk=episode_id,
            podcast=self.podcast,
            **attrs.asdict(item),
        )

    def extract_text(self, feed, categories):
        text = " ".join(
            value
            for value in [
                self.podcast.title,
                self.podcast.description,
                self.podcast.keywords,
                self.podcast.owner,
            ]
            + [c.name for c in categories]
            + [item.title for item in feed.items][:6]
            if value
        )
        return " ".join(text_parser.extract_keywords(self.podcast.language, text))

    def get_feed_headers(self):
        headers = {
            "Accept": ACCEPT_HEADER,
            "User-Agent": get_user_agent(),
        }

        if self.podcast.etag:
            headers["If-None-Match"] = quote_etag(self.podcast.etag)
        if self.podcast.modified:
            headers["If-Modified-Since"] = http_date(self.podcast.modified.timestamp())
        return headers


@functools.lru_cache
def get_categories_dict():
    return Category.objects.in_bulk(field_name="name")


def make_content_hash(content):
    return hashlib.sha256(content).hexdigest()
