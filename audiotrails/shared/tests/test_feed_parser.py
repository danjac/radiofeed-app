from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from audiotrails.shared.feed_parser import Audio, Feed, Item


class AudioModelTests(SimpleTestCase):
    url = "https://www.podtrac.com/pts/redirect.mp3/traffic.megaphone.fm/TSK8060512733.mp3"

    def test_audio(self) -> None:
        Audio(type="audio/mpeg", url=self.url)

    def test_not_audio(self) -> None:
        self.assertRaises(ValidationError, Audio, type="text/xml", url=self.url)


class FeedModelTests(SimpleTestCase):
    website = "http://reddit.com"

    def setUp(self) -> None:
        self.item = Item(
            audio=Audio(
                type="audio/mpeg",
                rel="enclosure",
                url="https://www.podtrac.com/pts/redirect.mp3/traffic.megaphone.fm/TSK8060512733.mp3",
            ),
            title="test",
            guid="test",
            raw_pub_date="Fri, 12 Jun 2020 17:33:46 +0000",
            duration="2000",
        )

    def test_language(self) -> None:

        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link=self.website,
            language="en-gb",
            categories=[],
        )

        self.assertEqual(feed.language, "en")

    def test_language_with_spaces(self) -> None:

        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link=self.website,
            language=" en-us",
            categories=[],
        )

        self.assertEqual(feed.language, "en")

    def test_language_with_single_value(self) -> None:

        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link=self.website,
            language="fi",
            categories=[],
        )

        self.assertEqual(feed.language, "fi")

    def test_language_with_empty(self) -> None:

        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link=self.website,
            language="",
            categories=[],
        )

        self.assertEqual(feed.language, "en")

    def test_valid_link(self) -> None:
        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link=self.website,
            categories=[],
        )

        self.assertEqual(feed.link, self.website)

    def test_empty_link(self) -> None:
        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link="",
            categories=[],
        )

        self.assertEqual(feed.link, "")

    def test_missing_http(self) -> None:
        feed = Feed(
            title="test",
            description="test",
            items=[self.item],
            creators=set(),
            image=None,
            link="politicology.com",
            categories=[],
        )

        self.assertEqual(feed.link, "http://politicology.com")
