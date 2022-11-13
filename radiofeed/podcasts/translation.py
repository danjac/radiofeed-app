from __future__ import annotations

from modeltranslation.translator import TranslationOptions, translator

from radiofeed.podcasts.models import Category


class CategoryTranslationOptions(TranslationOptions):
    """Translations of all category names."""

    fields = ("name",)


translator.register(Category, CategoryTranslationOptions)
