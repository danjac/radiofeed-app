import pytest
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertTemplateUsed

from simplecasts.tests.asserts import (
    assert200,
)
from simplecasts.tests.factories import (
    PodcastFactory,
)

_discover_url = reverse_lazy("podcasts:discover")


class TestSearchPeople:
    @pytest.mark.django_db
    def test_get(self, client, auth_user, faker):
        podcast = PodcastFactory(owner=faker.name())
        response = client.get(
            reverse("podcasts:search_people"),
            {
                "search": podcast.cleaned_owner,
            },
        )
        assert200(response)
        assertTemplateUsed(response, "search/search_people.html")

    @pytest.mark.django_db
    def test_empty(self, client, auth_user):
        response = client.get(reverse("podcasts:search_people"), {"search": ""})
        assert response.url == _discover_url
