# Django
from django import forms

# Local
from .models import Podcast


class PodcastForm(forms.ModelForm):
    class Meta:
        model = Podcast
        fields = ("title", "rss", "itunes")
