"""
Django settings for bet project.

Generated by 'django-admin startproject' using Django 3.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
import os
import sys
from pathlib import Path
import django_heroku

# Build paths inside the project like this: BASE_DIR / 'subdir'.
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = os.path.dirname(__file__)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-9kbj6b9n!c&d2*ts+0oj9$wf1m0i^tn^v6wslyg6@w(hv5ms7g'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'bet65.org']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 3rd party apps
    'django_admin_json_editor',
    'django_filters',
    'debug_toolbar',
    'rest_framework',
    'drf_yasg',
    'corsheaders',
    'log',
    # Apps
    'users',
    'betting',
    'api',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',  # Debug toolbar
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Corsheaders Middleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bet.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates', os.path.join(BASE_DIR, 'bet-front')]
        ,
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

WSGI_APPLICATION = 'bet.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases


if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'test.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'bet'),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'USER': os.environ.get('DB_USER', 'bet_admin'),
            'PASSWORD': os.environ.get('BET_ADMIN_DB_PASS', '1234')
        }
    }
# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Dhaka'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (os.path.join(BASE_DIR, 'bet-front', 'build', 'static'),
                    # BASE_DIR, str('static/')
                    )
STATIC_ROOT = os.path.join(BASE_DIR, str('static/'))

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom settings
# Rest Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [  #
        'users.backends.RestBackendWithJWT',  #
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100
}
if os.environ.get('LOCAL') == 'True':
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'].insert(0, 'rest_framework.authentication.SessionAuthentication')

# Authentication Settings
AUTHENTICATION_BACKENDS = (
    'users.backends.ModelBackendWithJWT',  # default
)
AUTH_USER_MODEL = 'users.User'
django_heroku.settings(locals())

# Corsheaders settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_URLS_REGEX = r'^/api/.*$'
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'POST',
    'PUT',
    'PATCH'
]

CORS_ALLOW_HEADERS = list(default_headers) + [
    'x-auth-token', 'club-token', 'AUTH_TOKEN',
]

JWK_KEY = os.environ.get('JWK_KEY', "{\"k\":\"TU6B5zRpJVD9pQ-86mEpQOf_N3gj-70kpGFQx30yUmW7PBDS"
                                    "RtAuavkWRfpQ_lXrc8m5Ga9ebqpe3fcPvIZVPQ\",\"kty\":\"oct\"}")

# Configuration
ADMIN_AUTH_TOKEN = os.environ.get('ADMIN_AUTH_TOKEN', 'eyJhbGciOiJIUzI1NiJ9.eyJiYWxhbmNlIjoiNjc2LjAwIiwiZW1haWwiOi'
                                                      'JnQGcuY29tIiwiZmlyc3RfbmFtZSI6IiIs'
                                                      'ImdhbWVfZWRpdG9yIjpmYWxzZSwiaWQiOjEsImlzX2NsdWJfYWRtaW4iOnRy'
                                                      'dWUsImlzX3N1cGVydXNlciI6dHJ1ZSwia'
                                                      'nd0IjoiTm90IGFsbG93ZWQgand0LiBQbGVhc2UgbG9naW4gdG8gZ2V0IEpXV'
                                                      'CIsImxhc3RfbmFtZSI6IiIsInBob25lIj'
                                                      'oiZHNhZGFmIiwicmVmZXJyZWRfYnkiOm51bGwsInVzZXJfY2x1YiI6MSwidXN'
                                                      'lcm5hbWUiOiJtYWgifQ.CqB1e1u9vIs5'
                                                      'nbgZZrnlvDFlMCiV3fU13yZMy24VDUU')

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': ADMIN_AUTH_TOKEN,
            'name': 'x-auth-token',
            'in': 'header'
        }
    }
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"  #
EMAIL_HOST = "mail.bet65.org"  #
EMAIL_HOST_USER = 'admin@bet65.org'  #
EMAIL_HOST_PASSWORD = 'e4mCoP,O'  #
EMAIL_PORT = 465  #
EMAIL_USE_SSL = True

INTERNAL_IPS = [
    # ...
    '127.0.0.1',
    # ...
]

if os.environ.get('LOG', 'False') == 'True':
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
                'datefmt': "%d/%b/%Y %H:%M:%S"
            },
            'simple': {
                'format': '%(levelname)s %(message)s'
            },
        },
        'handlers': {
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': 'mysite.log',
                'formatter': 'verbose'
            },
        },
        'loggers': {
            'django': {
                'handlers': ['file'],
                'propagate': True,
                'level': 'DEBUG',
            },
            'MYAPP': {
                'handlers': ['file'],
                'level': 'DEBUG',
            },
        }
    }
