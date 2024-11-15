import pytest
from django.core.paginator import EmptyPage, PageNotAnInteger

from radiofeed.paginator import CountlessPaginator


class TestCountlessPage:
    def test_is_empty(self):
        page = CountlessPaginator([], 10).get_page(1)
        assert repr(page) == "<Page 1>"
        assert len(page) == 0
        assert page.has_next() is False
        assert page.has_previous() is False
        assert page.has_other_pages() is False

    def test_has_only_one_page(self):
        items = [1, 2]
        page = CountlessPaginator(items, 10).get_page(1)
        assert repr(page) == "<Page 1>"
        assert len(page) == 2
        assert page.has_next() is False
        assert page.has_previous() is False
        assert page.has_other_pages() is False

    def test_has_next(self):
        items = [1, 2, 3]
        page = CountlessPaginator(items, 2).get_page(1)
        assert repr(page) == "<Page 1>"
        assert page.has_next() is True
        assert page.has_previous() is False
        assert page.has_other_pages() is True
        assert page.next_page_number() == 2
        with pytest.raises(EmptyPage):
            page.previous_page_number()

    def test_has_previous(self):
        items = [1, 2, 3]
        page = CountlessPaginator(items, 2).get_page(2)
        assert repr(page) == "<Page 2>"
        assert page.has_previous() is True
        assert page.has_next() is False
        assert page.has_other_pages() is True

        assert page.previous_page_number() == 1

        with pytest.raises(EmptyPage):
            page.next_page_number()


class TestCountlessPaginator:
    def test_validate_number_int(self):
        paginator = CountlessPaginator([], 10)
        assert paginator.validate_number(1) == 1

    def test_validate_number_less_than_1(self):
        paginator = CountlessPaginator([], 10)
        with pytest.raises(EmptyPage):
            paginator.validate_number(-1)

    def test_validate_number_str(self):
        paginator = CountlessPaginator([], 10)
        assert paginator.validate_number("1") == 1

    def test_validate_number_invalid(self):
        paginator = CountlessPaginator([], 10)

        with pytest.raises(PageNotAnInteger):
            paginator.validate_number("oops")

    def test_get_page_ok(self):
        paginator = CountlessPaginator([1, 2, 3], 2)
        page = paginator.get_page(2)
        assert len(page) == 1
        assert page.number == 2
        assert page.has_next() is False
        assert page.has_previous() is True

    def test_get_page_empty(self):
        paginator = CountlessPaginator([], 2)
        page = paginator.get_page(1)
        assert len(page) == 0
        assert page.number == 1
        assert page.has_next() is False
        assert page.has_previous() is False

    def test_get_page_only_one_page(self):
        paginator = CountlessPaginator([1, 2], 10)
        page = paginator.get_page(1)
        assert len(page) == 2
        assert page.number == 1
        assert page.has_next() is False
        assert page.has_previous() is False
