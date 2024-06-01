from listenwave.checks import check_secure_admin_url


class TestCheckSecureAdminUrl:
    def test_admin_url_secure(self, settings):
        settings.ADMIN_URL = "i-am-ok/"
        assert len(check_secure_admin_url([])) == 0

    def test_admin_url_insecure(self, settings):
        settings.ADMIN_URL = "admin/"
        assert len(check_secure_admin_url([])) == 1
