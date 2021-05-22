from audiotrails.config.settings.base import env

AWS_MEDIA_LOCATION = env("AWS_MEDIA_LOCATION", default="media")
AWS_STATIC_LOCATION = env("AWS_STATIC_LOCATION", default="static")

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default=None)
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default=None)
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default=None)
AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="eu-north-1")

AWS_QUERYSTRING_AUTH = False
AWS_IS_GZIPPED = True
AWS_DEFAULT_ACL = "public-read"

AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=600"}

AWS_STATIC_CLOUDFRONT_DOMAIN = env("AWS_STATIC_CLOUDFRONT_DOMAIN", default=None)
