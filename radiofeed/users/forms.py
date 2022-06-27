from django import forms
from django.utils.datastructures import OrderedSet

from radiofeed.podcasts.parsers import opml_parser
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

    def parse_opml_feeds(self, limit=300):
        self.cleaned_data["opml"].seek(0)
        try:
            feeds = [
                outline.rss
                for outline in opml_parser.parse_opml(self.cleaned_data["opml"].read())
                if outline.rss
            ][:limit]
        except opml_parser.OpmlParserError:
            feeds = []
        return OrderedSet(feeds)
