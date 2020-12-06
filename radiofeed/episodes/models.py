# Django
from django.db import models
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils.text import slugify

# RadioFeed
from radiofeed.podcasts.models import Podcast


class Episode(models.Model):

    podcast = models.ForeignKey(Podcast, on_delete=models.CASCADE)

    guid = models.TextField()

    pub_date = models.DateTimeField()
    link = models.URLField(null=True, blank=True, max_length=500)

    title = models.TextField(blank=True)
    description = models.TextField(blank=True)
    keywords = models.TextField(blank=True)

    media_url = models.URLField(max_length=500)
    media_type = models.CharField(max_length=20)
    length = models.IntegerField(null=True, blank=True)

    duration = models.CharField(max_length=12, blank=True)
    explicit = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["podcast", "guid"], name="unique_episode")
        ]
        indexes = [
            models.Index(fields=["podcast"]),
            models.Index(fields=["guid"]),
            models.Index(fields=["-pub_date"]),
            models.Index(fields=["pub_date"]),
            models.Index(fields=["title"]),
            models.Index(fields=["-title"]),
        ]

    def __str__(self):
        return self.title or self.guid

    def get_absolute_url(self):
        return reverse("episodes:episode_detail", args=[self.id, self.slug])

    @property
    def slug(self):
        return slugify(self.title, allow_unicode=False) or "episode"

    @property
    def file_size(self):
        return filesizeformat(self.length) if self.length else None
