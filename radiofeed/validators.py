from django.core.validators import URLValidator

http_url_validator = URLValidator(schemes=["http", "https"])
