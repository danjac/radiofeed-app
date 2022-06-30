import lxml

from django import forms

from radiofeed.common.parsers import xml_parser
from radiofeed.podcasts.models import Podcast, Subscription
from radiofeed.users.models import User


class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("send_email_notifications",)
        help_texts = {
            "send_email_notifications": "I'd like to receive notications of new content and recommendations.",
        }


class OpmlUploadForm(forms.Form):
    opml = forms.FileField(
        label="Select OPML file",
        widget=forms.FileInput(
            attrs={
                "accept": ",".join(
                    [
                        ".opml",
                        ".xml",
                        "application/xml",
                        "text/x-opml",
                        "text/xml",
                    ]
                )
            }
        ),
    )

    def subscribe_to_feeds(self, user, limit=300):

        try:
            feeds = self.parse_opml()
        except lxml.etree.XMLSyntaxError:
            return 0

        podcasts = (
            Podcast.objects.filter(rss__in=feeds)
            .exclude(subscription__user=user)
            .distinct()
        )[:limit]

        Subscription.objects.bulk_create(
            [Subscription(podcast=podcast, user=user) for podcast in podcasts],
            ignore_conflicts=True,
        )

        return podcasts.count()

    def parse_opml(self):
        self.cleaned_data["opml"].seek(0)

        for element in xml_parser.iterparse(
            self.cleaned_data["opml"].read(), "outline"
        ):
            with xml_parser.xpath(element) as xpath:
                if rss := xpath.first("@xmlUrl"):
                    yield rss
