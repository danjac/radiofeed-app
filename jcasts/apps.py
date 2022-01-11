from django.contrib.admin.apps import AdminConfig as BaseAdminConfig


class AdminConfig(BaseAdminConfig):

    # https://docs.djangoproject.com/en/4.0/ref/contrib/admin/#overriding-the-default-admin-site
    default_site = "jcasts.core.admin.AdminSite"
