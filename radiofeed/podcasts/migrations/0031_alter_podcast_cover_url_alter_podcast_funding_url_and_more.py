# Generated by Django 5.2 on 2025-04-03 17:33

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("podcasts", "0030_alter_podcast_cover_url_alter_podcast_funding_url_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="podcast",
            name="cover_url",
            field=models.URLField(
                blank=True,
                max_length=2083,
                validators=[
                    django.core.validators.URLValidator(schemes=["http", "https"])
                ],
            ),
        ),
        migrations.AlterField(
            model_name="podcast",
            name="funding_url",
            field=models.URLField(
                blank=True,
                max_length=2083,
                validators=[
                    django.core.validators.URLValidator(schemes=["http", "https"])
                ],
            ),
        ),
        migrations.AlterField(
            model_name="podcast",
            name="rss",
            field=models.URLField(
                max_length=2083,
                unique=True,
                validators=[
                    django.core.validators.URLValidator(schemes=["http", "https"])
                ],
            ),
        ),
        migrations.AlterField(
            model_name="podcast",
            name="website",
            field=models.URLField(
                blank=True,
                max_length=2083,
                validators=[
                    django.core.validators.URLValidator(schemes=["http", "https"])
                ],
            ),
        ),
    ]
