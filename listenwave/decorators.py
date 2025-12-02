from django.views.decorators.http import require_http_methods

require_form_methods = require_http_methods(["GET", "HEAD", "POST"])

require_DELETE = require_http_methods(["DELETE"])  # noqa: N816
