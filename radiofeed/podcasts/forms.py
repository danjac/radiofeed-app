from typing import TYPE_CHECKING, ClassVar

from django import forms

from radiofeed.parsers.opml_parser import parse_opml
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.opml_parser import parse_opml

if TYPE_CHECKING:
    from collections.abc import Iterator

if TYPE_CHECKING:
    from collections.abc import Iterator


class PodcastForm(forms.ModelForm):
    """Form to add a new podcast feed."""

    class Meta:
        model = Podcast
        fields: ClassVar[list] = ["rss"]
        labels: ClassVar[dict] = {"rss": "RSS Feed URL"}
        error_messages: ClassVar[dict] = {
            "rss": {"unique": "This podcast is not available"}
        }


class OpmlUploadForm(forms.Form):
    """Form for uploading OPML collection."""

    opml = forms.FileField(
        label="Select OPML file",
        widget=forms.FileInput(
            attrs={
                "accept": ".opml,.xml,application/xml,text/x-opml,text/xml",
            }
        ),
    )

    def parse_opml(self) -> Iterator[str]:
        """Parse the uploaded OPML file and extract podcast RSS feed URLs."""
        fp = self.cleaned_data["opml"]
        fp.seek(0)
        return parse_opml(fp.read())
