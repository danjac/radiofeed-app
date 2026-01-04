import pytest
from django.core.paginator import EmptyPage, PageNotAnInteger

from simplecasts.views.paginator import Paginator, validate_page_number


class TestPage:
    def test_is_empty(self):
        page = Paginator([], 10).get_page(1)
        assert repr(page) == "<Page 1>"
        assert len(page) == 0
        assert page.has_next is False
        assert page.has_previous is False
        assert page.has_other_pages is False

    def test_has_only_one_page(self):
        items = [1, 2]
        page = Paginator(items, 10).get_page(1)
        assert repr(page) == "<Page 1>"
        assert len(page) == 2
        assert page.has_next is False
        assert page.has_previous is False
        assert page.has_other_pages is False

    def test_has_next(self):
        items = [1, 2, 3]
        page = Paginator(items, 2).get_page(1)
        assert repr(page) == "<Page 1>"
        assert page.has_next is True
        assert page.has_previous is False
        assert page.has_other_pages is True
        assert page.next_page_number == 2
        with pytest.raises(EmptyPage):
            assert page.previous_page_number

    def test_has_previous(self):
        items = [1, 2, 3]
        page = Paginator(items, 2).get_page(2)
        assert repr(page) == "<Page 2>"
        assert page.has_previous is True
        assert page.has_next is False
        assert page.has_other_pages is True

        assert page.previous_page_number == 1

        with pytest.raises(EmptyPage):
            assert page.next_page_number


class TestValidatePageNumber:
    def test_int(self):
        assert validate_page_number(1) == 1

    def test_less_than_1(self):
        with pytest.raises(EmptyPage):
            validate_page_number(-1)

    def test_str(self):
        assert validate_page_number("1") == 1

    def test_invalid(self):
        with pytest.raises(PageNotAnInteger):
            validate_page_number("oops")


class TestPaginator:
    def test_get_page_ok(self):
        paginator = Paginator([1, 2, 3], 2)
        page = paginator.get_page(2)
        assert len(page) == 1
        assert page.number == 2
        assert page.has_next is False
        assert page.has_previous is True

    def test_get_page_str(self):
        paginator = Paginator([1, 2, 3], 2)
        page = paginator.get_page("2")
        assert len(page) == 1
        assert page.number == 2
        assert page.has_next is False
        assert page.has_previous is True

    def test_get_page_empty_str(self):
        paginator = Paginator([1, 2, 3], 2)
        page = paginator.get_page("")
        assert len(page) == 2
        assert page.number == 1
        assert page.has_next is True
        assert page.has_previous is False

    def test_get_page_bad_str(self):
        paginator = Paginator([1, 2, 3], 2)
        page = paginator.get_page("bad")
        assert len(page) == 2
        assert page.number == 1
        assert page.has_next is True
        assert page.has_previous is False

    def test_get_page_empty(self):
        paginator = Paginator([], 2)
        page = paginator.get_page(1)
        assert len(page) == 0
        assert page.number == 1
        assert page.has_next is False
        assert page.has_previous is False

    def test_get_page_only_one_page(self):
        paginator = Paginator([1, 2], 10)
        page = paginator.get_page(1)
        assert len(page) == 2
        assert page.number == 1
        assert page.has_next is False
        assert page.has_previous is False
