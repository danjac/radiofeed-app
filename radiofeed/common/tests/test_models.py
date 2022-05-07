from radiofeed.common.models import SiteConfiguration


class TestSiteConfigurationModel:
    def test_str(self):
        return str(SiteConfiguration(site_name="Test Site")) == "Test Site"
