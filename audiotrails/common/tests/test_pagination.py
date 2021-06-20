import http

from django.http import Http404
from django.test import RequestFactory, TestCase

from audiotrails.common.middleware import HtmxDetails
from audiotrails.common.pagination import paginate, render_paginated_response
from audiotrails.podcasts.factories import PodcastFactory


class RenderPaginationResponseTests(TestCase):
    main_template = "podcasts/index.html"
    pagination_template = "podcasts/_podcasts.html"

    @classmethod
    def setUpTestData(cls) -> None:
        cls.podcasts = PodcastFactory.create_batch(30)

    def setUp(self) -> None:
        self.rf = RequestFactory()

    def test_is_not_htmx(self) -> None:
        req = self.rf.get("/", {"page": "2"})
        req.htmx = HtmxDetails(req)
        resp = render_paginated_response(
            req,
            self.podcasts,
            self.main_template,
            self.pagination_template,
            page_size=10,
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.template_name, self.main_template)
        self.assertNotIn("is_paginated", resp.context_data)

    def test_is_htmx(self) -> None:
        req = self.rf.get(
            "/",
            {"page": "2"},
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="page-2",
        )
        req.htmx = HtmxDetails(req)
        resp = render_paginated_response(
            req,
            self.podcasts,
            self.main_template,
            self.pagination_template,
            page_size=10,
        )
        self.assertEqual(resp.status_code, http.HTTPStatus.OK)
        self.assertEqual(resp.template_name, self.pagination_template)
        self.assertTrue(resp.context_data["is_paginated"])


class PaginateTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.podcasts = PodcastFactory.create_batch(30)

    def setUp(self) -> None:
        self.rf = RequestFactory()

    def test_paginate_first_page(self) -> None:
        page = paginate(self.rf.get("/"), self.podcasts, page_size=10)
        self.assertEqual(page.number, 1)
        self.assertTrue(page.has_next())
        self.assertFalse(page.has_previous())
        self.assertEqual(page.paginator.num_pages, 3)

    def test_paginate_specified_page(self) -> None:
        page = paginate(self.rf.get("/", {"page": "2"}), self.podcasts, page_size=10)
        self.assertEqual(page.number, 2)
        self.assertTrue(page.has_next())
        self.assertTrue(page.has_previous())
        self.assertEqual(page.paginator.num_pages, 3)

    def test_paginate_invalid_page(self) -> None:
        self.assertRaises(
            Http404,
            paginate,
            self.rf.get("/", {"page": "fubar"}),
            self.podcasts,
            page_size=10,
        )
