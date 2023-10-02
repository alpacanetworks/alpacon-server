"""
Django settings for alpacon project.
"""

import os
import ldap

from datetime import timedelta
from distutils.util import strtobool

from django.contrib.messages import constants as messages
from django.core.management.utils import get_random_secret_key

from celery.schedules import schedule, crontab
from django.utils import timezone

from django_auth_ldap.config import LDAPSearch, GroupOfNamesType


SECRET_KEY = os.getenv('ALPACON_SECRET_KEY', get_random_secret_key())

DEBUG = bool(strtobool(os.getenv('ALPACON_DEBUG', 'false')))

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_HOSTS = os.getenv('ALPACON_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

URL_PREFIX = os.getenv('ALPACON_URL_PREFIX', 'http://localhost:8000')
URL_ROOT = os.getenv('ALPACON_ROOT', '/')

REACT_URL = os.getenv('ALPACON_REACT_URL', 'http://localhost:3000')

CORS_ALLOW_CREDENTIALS = bool(strtobool(os.getenv('ALPACON_CORS_ALLOW_CREDENTIALS', 'true')))
CORS_ALLOWED_ORIGINS = os.getenv('ALPACON_CORS_ALLOWED_ORIGINS', REACT_URL).split(',')
CSRF_TRUSTED_ORIGINS = os.getenv('ALPACON_CSRF_TRUSTED_ORIGINS', REACT_URL).split(',')
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
    'BLOB'
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    "content-disposition",
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'responsetype'
]

CORS_EXPOSE_HEADERS = [
    "content-disposition",
]

IS_BEHIND_PROXY = bool(strtobool(os.getenv('ALPACON_IS_BEHIND_PROXY', 'false')))
if IS_BEHIND_PROXY:
    USE_X_FORWARDED_PORT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition

INSTALLED_APPS = [
    'servers',
    'websh',
    'proc',
    'history',
    'events',
    'packages',
    'l2utils',
    'notifications',
    'utils',
    'iam',
    'profiles',
    'api',
    'api.api_auth',
    'api.apiclient',
    'api.apitoken',
    'api.password_reset',
    'wsutils',
    'telemetry',
    'template_utils',
    'corsheaders',
    'channels',
    'daphne',
    'rest_framework',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

REST_API_APPS = [
    'iam',
    'profiles',
    'servers',
    'packages',
    'websh',
    'proc',
    'history',
    'events',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'alpacon.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'alpacon/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'alpacon.wsgi.application'
ASGI_APPLICATION = 'alpacon.asgi.application'

AUTH_USER_MODEL = 'iam.User'

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'django_auth_ldap.backend.LDAPBackend',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DATABASES = {
    'default': {
        'ENGINE': os.getenv('ALPACON_DB_ENGINE', 'django.db.backends.postgresql'),
        'HOST': os.getenv('ALPACON_DB_HOST', 'localhost'),
        'NAME': os.getenv('POSTGRES_DB', 'alpacon'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
    },
}

REDIS_HOST = os.getenv('ALPACON_REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('ALPACON_REDIS_PORT', '6379'))

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(REDIS_HOST, REDIS_PORT)],
        },
    },
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES':[
        'rest_framework.authentication.SessionAuthentication',
        'api.apiclient.auth.APIClientAuthentication',
        'api.apitoken.auth.APITokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'api.pagination.MyPageNumberPagination',
    'PAGE_SIZE': 15,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
    messages.SUCCESS: 'success',
}

# Internationalization

LANGUAGE_CODE = os.getenv('ALPACON_LANGUAGE_CODE', 'en-us')

TIME_ZONE = os.getenv('TZ', 'Asia/Seoul')

USE_I18N = True

USE_L10N = True

USE_TZ = True

PHONENUMBER_DB_FORMAT = 'E164'
PHONENUMBER_DEFAULT_FORMAT = 'INTERNATIONAL'

LOGIN_VALID_DAYS = 7
PASSWORD_RESET_TIMEOUT = 6*60*60 # in seconds

WEBSH_SESSION_SHARE_TIMEOUT = timedelta(minutes=30)

EMAIL_BACKEND = os.getenv('ALPACON_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_FROM = os.getenv('ALPACON_EMAIL_FROM', 'no-reply@alpacon.io')
EMAIL_SUBJECT_PREFIX = os.getenv('ALPACON_EMAIL_SUBJECT_PREFIX', '[alpacon] ')

# SMTP settings
EMAIL_HOST = os.getenv('ALPACON_EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('ALPACON_EMAIL_PORT', '25'))
EMAIL_HOST_USER = os.getenv('ALPACON_EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('ALPACON_EMAIL_HOST_PASSWORD')
EMAIL_USE_LOCALTIME = bool(strtobool(os.getenv('ALPACON_EMAIL_USE_LOCALTIME', 'true')))
EMAIL_USE_TLS = bool(strtobool(os.getenv('ALPACON_EMAIL_USE_TLS', 'true')))

WEEKDAYS = 'mon,tue,wed,thu,fri'

CELERY_BROKER_URL = 'redis://%s:%d' % (REDIS_HOST, REDIS_PORT)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    'check_server_status': {
        'task': 'servers.tasks.check_server_status',
        'schedule': schedule(run_every=timedelta(seconds=5)),
    },
    'ping_all_servers': {
        'task': 'servers.tasks.ping_all_servers',
        'schedule': crontab(minute='*/5'),
    },
    'cleanup_installers': {
        'task': 'servers.tasks.cleanup_installers',
        'schedule': crontab('*/10'),
    },
    'clear_stale_sessions': {
        'task': 'wsutils.tasks.clear_stale_sessions',
        'schedule': crontab(),
    },
    'delete_old_sessions': {
        'task': 'wsutils.tasks.delete_old_sessions',
        'schedule': crontab(minute='*/10'),
    },
    'execute_scheduled_commands': {
        'task': 'events.tasks.execute_scheduled_commands',
        'schedule': schedule(run_every=timedelta(seconds=5)),
    },
    'delete_old_events': {
        'task': 'events.tasks.delete_old_events',
        'schedule': crontab(minute='*/10'),
    },
    'delete_old_commands': {
        'task': 'events.tasks.delete_old_commands',
        'schedule': crontab(minute='*/10'),
    },
    'delete_old_history': {
        'task': 'history.tasks.delete_old_history',
        'schedule': crontab(minute='*/10'),
    },
    'delete_expired_tokens': {
        'task': 'api.apitoken.tasks.delete_expired_tokens',
        'schedule': crontab(),
    },
    'update_mac_vendor_list': {
        'task': 'l2utils.tasks.update_mac_vendor_list',
        'schedule': crontab(minute=0, hour=7, day_of_week=WEEKDAYS),
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] (%(name)s) %(message)s'
        },
        'simple': {
            'format': '[%(levelname)s] %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'wsutils': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'daphne': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# LDAP
USE_AUTH_LDAP_BACKEND = bool(strtobool(os.getenv('USE_AUTH_LDAP_BACKEND', 'false')))

LDAP_BASE = os.getenv('LDAP_DOMAIN', 'example.com')
LDAP_BASE_DN = 'dc=' + LDAP_BASE.replace('.', ',dc=')

LDAP_USER_BASE = f"ou=users,{LDAP_BASE_DN}"
LDAP_GROUP_BASE = f"ou=groups,{LDAP_BASE_DN}"

AUTH_LDAP_SERVER_URI = os.getenv('LDAP_SERVER_URI', 'ldap://localhost:389')
AUTH_LDAP_START_TLS = bool(strtobool(os.getenv('LDAP_START_TLS', 'false')))
AUTH_LDAP_BIND_DN = 'cn=%(username)s,%(base_dn)s' % {
    'username': os.getenv('LDAP_ADMIN_USERNAME', 'admin'),
    'base_dn': LDAP_BASE_DN,
}
AUTH_LDAP_BIND_PASSWORD = os.getenv('LDAP_ADMIN_PASSWORD', '')

AUTH_LDAP_USER_DN_TEMPLATE = 'uid=%%(user)s,%s' % LDAP_USER_BASE
AUTH_LDAP_GROUP_DN_TEMPLATE = "cn=%%(group)s,%s" % LDAP_GROUP_BASE
AUTH_LDAP_USER_ATTR_MAP = {
    'first_name': 'givenName',
    'last_name': 'sn',
    'email': 'mail'
}

AUTH_LDAP_USER_SEARCH = LDAPSearch(LDAP_USER_BASE,
    ldap.SCOPE_SUBTREE, "(uid=%(user)s)"
)

AUTH_LDAP_GROUP_SEARCH = LDAPSearch(LDAP_GROUP_BASE,
    ldap.SCOPE_SUBTREE, '(objectClass=groupOfNames)'
)

AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()
# AUTH_LDAP_REQUIRE_GROUP = 'cn=alpacon-users,%s' % LDAP_GROUP_BASE
#
# AUTH_LDAP_USER_FLAGS_BY_GROUP = {
#     'is_active': 'cn=alpacon-users,%s' % LDAP_GROUP_BASE,
#     'is_staff': 'cn=admin-users,%s' % LDAP_GROUP_BASE,
#     'is_superuser': 'cn=superusers,%s' % LDAP_GROUP_BASE,
# }
AUTH_LDAP_FIND_GROUP_PERMS = False
AUTH_LDAP_MIRROR_GROUPS = False

try:
    from alpacon.local_settings import *
except ImportError:
    pass

LOGIN_URL = URL_ROOT + 'iam/login/'
LOGIN_REDIRECT_URL = URL_ROOT
LOGOUT_REDIRECT_URL = LOGIN_URL

# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
MEDIA_URL = URL_ROOT + 'media/'
