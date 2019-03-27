import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# If we actually did anything that used the secret key we'd need to set it to
# some constant value and find a way to secretly store it. However, pfif-tools
# doesn't use it for anything, we just need to set it to something to make
# Django happy.
SECRET_KEY = os.urandom(30)

if 'Development' in os.environ.get('SERVER_SOFTWARE', ''):
    DEBUG = True
    # If DEBUG is True and ALLOWED_HOSTS is empty, Django permits localhost.
    ALLOWED_HOSTS = []
else:
    DEBUG = False
    ALLOWED_HOSTS = ['pfif-tools.appspot.com']


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
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'


# Internationalization

LANGUAGE_CODE = 'en'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
