# Generated by Django 5.2.1 on 2025-05-27 14:56

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("podcasts", "0034_alter_podcast_updated"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="recommendation",
            name="podcasts_re_score_c89df8_idx",
        ),
        migrations.RemoveField(
            model_name="recommendation",
            name="score",
        ),
    ]
