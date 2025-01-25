from radiofeed.context_processors import csrf_header


class TestCsrfHeader:
    def test_csrf_header(self, rf):
        # Arrange
        request = rf.get("/")

        # Act
        result = csrf_header(request)

        # Assert
        assert result == {"csrf_header": "x-csrftoken"}
