from django.test import SimpleTestCase

from audiotrails.podcasts.text_parser import clean_text, extract_keywords


class ExtractKeywordsTests(SimpleTestCase):
    def test_extract(self) -> None:
        self.assertEqual(
            extract_keywords("en", "the cat sits on the mat"),
            [
                "cat",
                "sits",
                "mat",
            ],
        )


class CleanTextTests(SimpleTestCase):
    def test_remove_html_tags(self) -> None:
        self.assertEqual(clean_text("<p>test</p>"), "test")

    def test_remove_numbers(self) -> None:
        self.assertEqual(
            clean_text("Tuesday, September 1st, 2020"), "Tuesday September st "
        )
