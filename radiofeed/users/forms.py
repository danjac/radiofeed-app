from __future__ import annotations

from django import forms

from radiofeed.podcasts.parsers import opml_parser
from radiofeed.users.models import User


class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = User
        fields: tuple[str, ...] = ("send_email_notifications",)
        help_texts: dict[str, str] = {
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
                        "text/x-opml+xml",
                        "text/xml",
                    ]
                )
            }
        ),
    )

    def parse_opml_feeds(self, limit: int = 300) -> list[str]:
        self.cleaned_data["opml"].seek(0)
        try:
            return [
                outline.rss
                for outline in opml_parser.parse_opml(self.cleaned_data["opml"].read())
                if outline.rss
            ][:limit]
        except opml_parser.OpmlParserError:
            return []
