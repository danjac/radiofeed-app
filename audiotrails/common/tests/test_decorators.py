import http

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, TestCase

from audiotrails.common.decorators import ajax_login_required
from audiotrails.users.factories import UserFactory


@ajax_login_required
def my_ajax_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


class AjaxLoginRequiredTests(TestCase):
    def setUp(self) -> None:
        self.rf = RequestFactory()

    def test_anonymous(self) -> None:
        req = self.rf.get("/")
        req.user = AnonymousUser()
        self.assertRaises(PermissionDenied, my_ajax_view, req)

    def test_authenticated(self) -> None:
        req = self.rf.get("/")
        req.user = UserFactory()
        self.assertEqual(my_ajax_view(req).status_code, http.HTTPStatus.OK)
