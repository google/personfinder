# Copyright 2019 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module for Django settings."""

import os

import const
import site_settings

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# If we actually did anything that used the secret key we'd need to set it to
# some constant value and find a way to secretly store it. However, we don't use
# it for anything. We need to set it to something to make Django happy though,
# and we set it to something random to be safe in case we unknowingly do
# something in the future that uses it (better to have a password reset token
# break because this changed or something like that than a security hole we
# don't know about).
SECRET_KEY = os.urandom(30)

# Check if we're running a local development server or in prod.
if os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
    DEBUG = True
    DEBUG_PROPAGATE_EXCEPTIONS = True
    ALLOWED_HOSTS = ['*']
    SECURE_SSL_REDIRECT = False
else:
    DEBUG = False
    DEBUG_PROPAGATE_EXCEPTIONS = False
    ALLOWED_HOSTS = site_settings.PROD_ALLOWED_HOSTS
    SECURE_SSL_REDIRECT = True

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'csp.middleware.CSPMiddleware',
]

ROOT_URLCONF = 'urls'

# By default, if a URL can't be resolved and doesn't end in a slash, Django will
# issue a redirect to the same URL with a slash. We'd rather not issue
# unecessary redirects, so we just put optional trailing slashes in the URL
# configuration.
APPEND_SLASH = False

# App Engine issues HTTP requests for tasks, so we don't force HTTPS for them.
SECURE_REDIRECT_EXEMPT = [r'^.*/tasks/.*']
if site_settings.OPTIONAL_PATH_PREFIX:
  SECURE_REDIRECT_EXEMPT += [
      r'^%s/.*/tasks/.*' % site_settings.OPTIONAL_PATH_PREFIX]

# Based on the Strict CSP example here:
# https://csp.withgoogle.com/docs/strict-csp.html
CSP_INCLUDE_NONCE_IN = ('script-src', 'style-src')
CSP_BASE_URI = "'none'"
CSP_OBJECT_SRC = "'none'"
CSP_SCRIPT_SRC = ("'unsafe-inline'", "'unsafe-eval'",
                  "'strict-dynamic' https: http:",)
CSP_STYLE_SRC = ("'unsafe-inline'", "'unsafe-eval'",
                 "'strict-dynamic' https: http:",)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['resources'],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'

# Internationalization

LANGUAGE_CODE = const.DEFAULT_LANGUAGE_CODE

LANGUAGES_BIDI = ['ar', 'he', 'fa', 'iw', 'ur']

USE_I18N = True

USE_L10N = True

LOCALE_PATHS = ['locale']

TIME_ZONE = 'UTC'

USE_TZ = True

# Static files

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'resources/static/fixed'),
]
