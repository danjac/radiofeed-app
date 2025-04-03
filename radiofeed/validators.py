from django.core.validators import URLValidator

url_validator = URLValidator(schemes=["http", "https"])
