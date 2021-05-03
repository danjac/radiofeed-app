import http

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from audiotrails.users.factories import UserFactory

from ..decorators import ajax_login_required


@ajax_login_required
def my_view(request):
    return HttpResponse()


class AjaxLoginRequiredTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_anonymous(self):
        req = self.rf.get("/")
        req.user = AnonymousUser()
        self.assertRaises(PermissionDenied, my_view, req)

    def test_authenticated(self):
        req = self.rf.get("/")
        req.user = UserFactory()
        self.assertEqual(my_view(req).status_code, http.HTTPStatus.OK)
