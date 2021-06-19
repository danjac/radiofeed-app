from django.test import SimpleTestCase

from audiotrails.podcasts.text_parser import clean_text, extract_keywords, get_stopwords


class StopwordsTests(SimpleTestCase):
    def test_get_stopwords_if_any(self):
        self.assertTrue(get_stopwords("en"))

    def test_get_stopwords_if_none(self):
        self.assertEqual(get_stopwords("ka"), [])


class ExtractKeywordsTests(SimpleTestCase):
    def test_extract_if_empty(self) -> None:
        self.assertEqual(extract_keywords("en", "   "), []),

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
