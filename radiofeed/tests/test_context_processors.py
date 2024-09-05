from radiofeed.context_processors import csrf_header


class TestCsrfHeader:
    def test_header(self, rf, settings):
        settings.CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"
        assert csrf_header(rf.get("/")) == {"CSRF_HEADER": "X-CSRFTOKEN"}
