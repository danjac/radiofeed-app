import pytest

from simplecasts.models.bookmarks import Bookmark
from simplecasts.tests.factories import BookmarkFactory


class TestBookmarkManager:
    @pytest.mark.django_db
    def test_search(self):
        bookmark1 = BookmarkFactory(
            episode__title="Learn Python Programming",
            episode__podcast__title="Tech Talks",
        )
        bookmark2 = BookmarkFactory(
            episode__title="Advanced Django Techniques",
            episode__podcast__title="Web Dev Weekly",
        )

        results = Bookmark.objects.search("Python")
        assert bookmark1 in results
        assert bookmark2 not in results
