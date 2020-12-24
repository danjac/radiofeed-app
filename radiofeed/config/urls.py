# Django
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

# RadioFeed
from radiofeed.users.views import account as account_views
from radiofeed.users.views import delete_account
from radiofeed.users.views import socialaccount as socialaccount_views
from radiofeed.users.views import user_preferences

urlpatterns = [
    path("", include("radiofeed.podcasts.urls")),
    path("episodes/", include("radiofeed.episodes.urls")),
    path("account/login/", account_views.login, name="account_login"),
    path("account/signup/", account_views.signup, name="account_signup"),
    path(
        "account/password/change/",
        account_views.password_change,
        name="account_change_password",
    ),
    path(
        "account/password/set/",
        account_views.password_set,
        name="account_set_password",
    ),
    path(
        "account/password/reset/",
        account_views.password_reset,
        name="account_reset_password",
    ),
    re_path(
        r"^account/password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$",
        account_views.password_reset_from_key,
        name="account_reset_password_from_key",
    ),
    path("account/email/", account_views.email, name="account_email",),
    path(
        "account/social/signup/",
        socialaccount_views.signup,
        name="socialaccount_signup",
    ),
    path("account/preferences/", user_preferences, name="user_preferences"),
    path("account/~delete/", delete_account, name="delete_account"),
    path("account/", include("allauth.urls")),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path(settings.ADMIN_URL, admin.site.urls),
]

if settings.DEBUG:

    if "silk" in settings.INSTALLED_APPS:
        urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

    # static views
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # allow preview/debugging of error views in development
    urlpatterns += [
        path("errors/400/", TemplateView.as_view(template_name="400.html")),
        path("errors/403/", TemplateView.as_view(template_name="403.html")),
        path("errors/404/", TemplateView.as_view(template_name="404.html")),
        path("errors/405/", TemplateView.as_view(template_name="405.html")),
        path("errors/500/", TemplateView.as_view(template_name="500.html")),
        path("errors/csrf/", TemplateView.as_view(template_name="403_csrf.html")),
    ]
