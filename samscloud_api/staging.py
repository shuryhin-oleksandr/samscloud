from .base import *
from datetime import timedelta
from django.conf import settings

DEBUG = True

ALLOWED_HOSTS = [
    '*',
    'localhost',
]


#postgres db settings

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'sams_cloud_stage',
        'USER': 'sams_cloud_stage',
        'PASSWORD': 'sams_cloud_stage',
        'HOST': 'localhost',
    }
}

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'staticfiles')
]

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'email-smtp.us-west-2.amazonaws.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'AKIAQDHHFW26MJEYB4G3'
EMAIL_HOST_PASSWORD = 'BBPPY5AnBmVHbY4V6Pynzm7VfT8jIjICC1TP96vKy4ex'
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'notifications@samscloud.io'

CORS_ORIGIN_ALLOW_ALL = True

# JWT_AUTH = {
#     # how long the original token is valid for
#     'JWT_EXPIRATION_DELTA': datetime.timedelta(days=7),

#     'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
#     'TOKEN_TYPE_CLAIM': 'token_type',

#     'JTI_CLAIM': 'jti',

#     'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
#     'SLIDING_TOKEN_LIFETIME': timedelta(days=5),
#     'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=8),
# }

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=28),
    # 'ACCESS_TOKEN_LIFETIME': timedelta(minutes=7200),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=28),
    # 'REFRESH_TOKEN_LIFETIME': timedelta(minutes=60),

}

FRONTEND_DOMAIN = 'web.samscloud.io'

try:
    from .local import *
except ImportError:
    pass


#celery settings

CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# s3 settings
#AWS_ACCESS_KEY_ID = 'AKIAQDHHFW26HQ2VZKFK'
#AWS_SECRET_ACCESS_KEY = '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'
#AWS_ACCESS_KEY_ID = 'AKIAQDHHFW26PJGK2PMF'
#AWS_SECRET_ACCESS_KEY = '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'
AWS_ACCESS_KEY_ID = 'AKIAQDHHFW26ITVAHF7F'
AWS_SECRET_ACCESS_KEY = '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'
AWS_STORAGE_BUCKET_NAME = 'samscloud-api'
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_LOCATION = 'static'

STATIC_URL = 'https://%s/%s/' % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)

STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

DEFAULT_FILE_STORAGE = 'samscloud_api.storage_backends.MediaStorage'
