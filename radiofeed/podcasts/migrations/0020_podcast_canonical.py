# Generated by Django 5.1.7 on 2025-03-10 14:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("podcasts", "0019_remove_podcast_podcasts_po_rating_f96c31_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="podcast",
            name="canonical",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="duplicates",
                to="podcasts.podcast",
            ),
        ),
    ]
