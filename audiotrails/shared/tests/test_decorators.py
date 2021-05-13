import http
import json

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from audiotrails.users.factories import UserFactory

from ..decorators import accepts_json, ajax_login_required


@ajax_login_required
def my_ajax_view(request):
    return HttpResponse()


@accepts_json
def my_json_view(request):
    return HttpResponse()


class AjaxLoginRequiredTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_anonymous(self):
        req = self.rf.get("/")
        req.user = AnonymousUser()
        self.assertRaises(PermissionDenied, my_ajax_view, req)

    def test_authenticated(self):
        req = self.rf.get("/")
        req.user = UserFactory()
        self.assertEqual(my_ajax_view(req).status_code, http.HTTPStatus.OK)


class AcceptJsonTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_invalid_content_type(self):
        req = self.rf.post(
            "/", content_type="text/html", data=json.dumps({"testing": "ok"})
        )
        self.assertEqual(my_json_view(req).status_code, http.HTTPStatus.BAD_REQUEST)
        self.assertFalse(hasattr(req, "json"))

    def test_invalid_json(self):
        req = self.rf.post("/", content_type="application/json", data="testing")
        self.assertEqual(my_json_view(req).status_code, http.HTTPStatus.BAD_REQUEST)
        self.assertFalse(hasattr(req, "json"))

    def test_valid_json(self):
        req = self.rf.post(
            "/", content_type="application/json", data=json.dumps({"testing": "ok"})
        )
        self.assertEqual(my_json_view(req).status_code, http.HTTPStatus.OK)
        self.assertEqual(req.json, {"testing": "ok"})
