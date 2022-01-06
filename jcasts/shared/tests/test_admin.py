from jcasts.shared.admin import AdminSite


class TestAdminSite:
    def test_each_context(self, user, rf):
        req = rf.get("/")
        req.user = user
        dct = AdminSite().each_context(req)
        assert dct["site_header"] == "example.com Administration"
