import pytest
from django.urls import reverse_lazy

from simplecasts.tests.asserts import (
    assert200,
)
from simplecasts.tests.factories import (
    CategoryFactory,
    PodcastFactory,
)


class TestCategoryList:
    url = reverse_lazy("categories:index")

    @pytest.mark.django_db
    def test_matching_podcasts(self, client, auth_user):
        for _ in range(3):
            category = CategoryFactory()
            category.podcasts.add(PodcastFactory())

        response = client.get(self.url)

        assert200(response)
        assert len(response.context["categories"]) == 3

    @pytest.mark.django_db
    def test_no_matching_podcasts(
        self,
        client,
        auth_user,
    ):
        CategoryFactory.create_batch(3)
        response = client.get(self.url)

        assert200(response)
        assert len(response.context["categories"]) == 0

    @pytest.mark.django_db
    def test_search(self, client, auth_user, category, faker):
        CategoryFactory.create_batch(3)

        category = CategoryFactory(name="testing")
        category.podcasts.add(PodcastFactory())

        response = client.get(self.url, {"search": "testing"})

        assert200(response)
        assert len(response.context["categories"]) == 1

    @pytest.mark.django_db
    def test_search_no_matching_podcasts(self, client, auth_user, category, faker):
        CategoryFactory.create_batch(3)

        CategoryFactory(name="testing")

        response = client.get(self.url, {"search": "testing"})

        assert200(response)
        assert len(response.context["categories"]) == 0


class TestCategoryDetail:
    @pytest.mark.django_db
    def test_get(self, client, auth_user, category):
        PodcastFactory.create_batch(12, categories=[category])
        response = client.get(category.get_absolute_url())
        assert200(response)
        assert response.context["category"] == category

    @pytest.mark.django_db
    def test_search(self, client, auth_user, category, faker):
        PodcastFactory.create_batch(12, title="zzzz", categories=[category])
        podcast = PodcastFactory(title=faker.unique.text(), categories=[category])

        response = client.get(category.get_absolute_url(), {"search": podcast.title})

        assert200(response)

        assert len(response.context["page"].object_list) == 1

    @pytest.mark.django_db
    def test_no_podcasts(self, client, auth_user, category):
        response = client.get(category.get_absolute_url())
        assert200(response)

        assert len(response.context["page"].object_list) == 0
