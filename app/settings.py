import os

import const


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


if os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
    DEBUG = True
    # If DEBUG is True and ALLOWED_HOSTS is empty, Django permits localhost.
    ALLOWED_HOSTS = []
else:
    DEBUG = False
    ALLOWED_HOSTS = [
        'googlepersonfinder.appspot.com',
        'google.org',
        'personfinder.google.org',
    ]


# Application definition

INSTALLED_APPS = [
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
        ],
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
            'loaders': [
                'template_loader.TemplateLoader',
            ]
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
