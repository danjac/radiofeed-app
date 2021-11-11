from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from django.contrib.auth import get_user_model

if TYPE_CHECKING:
    from django.contrib.auth.models import User
else:
    User = get_user_model()

ComparableT = TypeVar("ComparableT", bound="Comparable")


class Comparable(Protocol):
    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __lt__(self: ComparableT, other: ComparableT) -> bool:
        ...

    @abstractmethod
    def __gt__(self: ComparableT, other: ComparableT) -> bool:
        ...

    @abstractmethod
    def __le__(self: ComparableT, other: ComparableT) -> bool:
        ...

    @abstractmethod
    def __ge__(self: ComparableT, other: ComparableT) -> bool:
        ...
