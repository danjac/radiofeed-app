from typing import Any, Callable, Dict, Union

from django.http import HttpRequest, HttpResponse

HttpCallable = Callable[[HttpRequest], HttpResponse]

ContextDict = Dict[str, Any]

IntOrFloat = Union[int, float]
