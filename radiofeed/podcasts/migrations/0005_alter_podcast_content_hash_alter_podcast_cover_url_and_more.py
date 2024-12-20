# Generated by Django 5.1.1 on 2024-09-14 11:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("podcasts", "0004_alter_podcast_frequency"),
    ]

    operations = [
        migrations.AlterField(
            model_name="podcast",
            name="content_hash",
            field=models.CharField(blank=True, default="", max_length=64),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="podcast",
            name="cover_url",
            field=models.URLField(blank=True, default="", max_length=2083),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="podcast",
            name="funding_url",
            field=models.URLField(blank=True, default="", max_length=2083),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="podcast",
            name="parser_error",
            field=models.CharField(
                blank=True,
                choices=[
                    ("duplicate", "Duplicate"),
                    ("inaccessible", "Inaccessible"),
                    ("invalid_data", "Invalid Data"),
                    ("invalid_rss", "Invalid RSS"),
                    ("not_modified", "Not Modified"),
                    ("unavailable", "Unavailable"),
                ],
                default="",
                max_length=30,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="podcast",
            name="website",
            field=models.URLField(blank=True, default="", max_length=2083),
            preserve_default=False,
        ),
    ]
