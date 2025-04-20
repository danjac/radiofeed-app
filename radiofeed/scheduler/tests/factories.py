import factory
from django_apscheduler.models import DjangoJob, DjangoJobExecution


class DjangoJobFactory(factory.django.DjangoModelFactory):
    """Factory for creating DjangoJob instances."""

    class Meta:
        model = DjangoJob


class DjangoJobExecutionFactory(factory.django.DjangoModelFactory):
    """Factory for creating DjangoJobExecution instances."""

    job = factory.SubFactory(DjangoJobFactory)

    class Meta:
        model = DjangoJobExecution
