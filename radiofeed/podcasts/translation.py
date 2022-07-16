from __future__ import annotations

from modeltranslation.translator import TranslationOptions, translator

from .models import Category


class CategoryTranslationOptions(TranslationOptions):
    fields = ("name",)


translator.register(Category, CategoryTranslationOptions)
