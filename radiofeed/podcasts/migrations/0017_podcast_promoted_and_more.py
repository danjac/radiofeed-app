# Generated by Django 5.1.7 on 2025-03-09 13:09

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("podcasts", "0016_remove_podcast_podcasts_po_promote_fdc955_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="podcast",
            name="promoted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name="podcast",
            index=models.Index(
                fields=["promoted"], name="podcasts_po_promote_fdc955_idx"
            ),
        ),
    ]
