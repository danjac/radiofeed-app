import json
import pathlib

from datetime import datetime, timedelta

import pytest
import pytz

from django.utils import timezone
from pydantic import ValidationError

from jcasts.podcasts.feed_models import Item, ItunesResult, Link


class TestItunesResult:
    def test_get_cleaned_title(self):
        result = ItunesResult(
            collectionName="<b>test</b>",
            feedUrl="https://example.com/rss.xml",
            trackViewUrl="https://apple.com/feed",
            artworkUrl600="https://apple.com/test.jpg",
        )
        assert result.get_cleaned_title() == "test"


class TestLinkModel:
    def test_is_not_audio(self):
        link = Link(
            **{
                "rel": "alternate",
                "type": "text/html",
                "href": "https://play.acast.com/s/dansnowshistoryhit/theoriginsofenglish",
            },
        )
        assert link.is_audio() is False

    def test_is_audio(self):
        link = Link(
            **{
                "length": "55705268",
                "type": "audio/mpeg",
                "href": "https://sphinx.acast.com/channelhistoryhit/dansnowshistoryhit/theoriginsofenglish/media.mp3",
                "rel": "enclosure",
            }
        )

        assert link.is_audio() is True


class TestItemModel:
    @pytest.fixture
    def item_data(self):
        return json.load(
            open(pathlib.Path(__file__).parent / "mocks" / "feed_item.json", "rb")
        )

    def test_missing_audio(self, item_data):
        del item_data["links"]
        with pytest.raises(ValidationError):
            Item.parse_obj(item_data)

    def test_invalid_audio(self, item_data):
        item_data["links"] = [
            {
                "length": "55705268",
                "rel": "enclosure",
                "type": "audio/mpeg",
            },
        ]
        with pytest.raises(ValidationError):
            Item.parse_obj(item_data)

    def test_published(self, item_data):
        del item_data["published"]
        with pytest.raises(ValidationError):
            Item.parse_obj(item_data)

    def test_published_in_future(self, item_data):
        item_data["published"] = (timezone.now() + timedelta(days=1)).strftime(
            "%a, %d %b %Y %H:%M:%s"
        )
        with pytest.raises(ValidationError):
            Item.parse_obj(item_data)

    def test_missing_content(self, item_data):
        del item_data["content"]
        item = Item.parse_obj(item_data)
        assert item.description == ""

    def test_parse_complete_item(self, item_data):
        item = Item.parse_obj(item_data)

        assert item.id == "74561fff-4b98-4985-a36f-4970be28782e"
        assert item.title == "The Origins of English"
        assert item.published == datetime(2021, 8, 7, 4, 0, tzinfo=pytz.timezone("GMT"))

        assert item.itunes_duration == "00:38:34"
        assert item.itunes_episodetype == "full"
        assert item.itunes_explicit is False

        assert (
            item.link
            == "https://play.acast.com/s/dansnowshistoryhit/theoriginsofenglish"
        )

        assert item.image.href == (
            "https://thumborcdn.acast.com/AA9YH364rPs8gxGOwgyXGEvLhyo=/3000x3000/https://mediacdn.acast.com/assets/74561fff-4b98-4985-a36f-4970be28782e/cover-image-ks08c9r7-gonemedieval_square_3000x3000.jpg"
        )

        assert item.audio.href == (
            "https://sphinx.acast.com/channelhistoryhit/dansnowshistoryhit/theoriginsofenglish/media.mp3"
        )
        assert item.audio.length == 55705268
        assert item.audio.rel == "enclosure"
        assert item.audio.type == "audio/mpeg"

        assert item.summary == (
            "Approximately 1.35 billion people use it, either as a first or "
            "second language, so English and the way that we speak it has a "
            "daily impact on huge numbers of people. But how did the English "
            "language develop? In this episode from our sibling podcast Gone "
            "Medieval, Cat Jarman spoke to Eleanor Rye, an Associate Lecturer "
            "in English Language and Linguistics at the University of York. "
            "Using the present-day language, place names and dialects as "
            "evidence, Ellie shows us how English was impacted by a series of "
            "migrations.&nbsp;&nbsp; &#10;&nbsp;<br /><hr /><p>See <a "
            'href="https://acast.com/privacy" rel="noopener noreferrer" '
            'style="color: grey;" target="_blank">acast.com/privacy</a> for '
            "privacy and opt-out information.</p>"
        )

        assert item.description == (
            "<p>Approximately 1.35 billion people use it, either as "
            "a first or second language, so English and the way "
            "that we speak it has a daily impact on huge numbers of "
            "people. But how did the English language develop? In "
            "this episode from our sibling podcast <a "
            'href="https://podfollow.com/gone-medieval/view" '
            'rel="noopener noreferrer" target="_blank">Gone '
            "Medieval</a>, Cat Jarman spoke to Eleanor Rye, an "
            "Associate Lecturer in English Language and Linguistics "
            "at the University of York. Using the present-day "
            "language, place names and dialects as evidence, Ellie "
            "shows us how English was impacted by a series of "
            "migrations.&nbsp;&nbsp;</p> &#10;&nbsp;<br /><hr "
            '/><p>See <a href="https://acast.com/privacy" '
            'rel="noopener noreferrer" style="color: grey;" '
            'target="_blank">acast.com/privacy</a> for privacy and '
            "opt-out information.</p>"
        )
