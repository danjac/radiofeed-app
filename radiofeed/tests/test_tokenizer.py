from radiofeed.tokenizer import clean_text, get_stopwords, tokenize


class TestStopwords:
    def test_get_stopwords_if_any(self):
        assert get_stopwords("en")

    def test_get_stopwords_if_none(self):
        assert get_stopwords("ka") == set()


class TestTokenize:
    def test_extract_if_empty(self):
        assert tokenize("en", "   ") == []

    def test_extract(self):
        assert tokenize("en", "the cat sits on the mat") == [
            "cat",
            "sits",
            "mat",
        ]

    def test_extract_attribute_error(self, mocker):
        mocker.patch(
            "radiofeed.tokenizer._lemmatizer.lemmatize",
            side_effect=AttributeError,
        )
        assert tokenize("en", "the cat sits on the mat") == []


class TestCleanText:
    def test_remove_html_tags(self):
        assert clean_text("<p>test</p>") == "test"

    def test_remove_numbers(self):
        assert clean_text("Tuesday, September 1st, 2020") == "Tuesday September st "
