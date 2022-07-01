from radiofeed.common import text_parser


class TestStopwords:
    def test_get_stopwords_if_any(self):
        assert text_parser.get_stopwords("en")

    def test_get_stopwords_if_none(self):
        assert text_parser.get_stopwords("ka") == []


class TestExtractKeywords:
    def test_extract_if_empty(self):
        assert text_parser.extract_keywords("en", "   ") == []

    def test_extract(self):
        assert text_parser.extract_keywords("en", "the cat sits on the mat") == [
            "cat",
            "sits",
            "mat",
        ]

    def test_extract_attribute_error(self, mocker):
        mocker.patch(
            "radiofeed.common.text_parser.lemmatizer.lemmatize",
            side_effect=AttributeError,
        )
        assert text_parser.extract_keywords("en", "the cat sits on the mat") == []


class TestCleanText:
    def test_remove_html_tags(self):
        assert text_parser.clean_text("<p>test</p>") == "test"

    def test_remove_numbers(self):
        assert (
            text_parser.clean_text("Tuesday, September 1st, 2020")
            == "Tuesday September st "
        )
