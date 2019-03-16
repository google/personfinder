#!/usr/bin/python2.7
# Copyright 2010 Google Inc.
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

"""Initialize Django and its internationalization machinery.

In any file that uses django modules, always import django_setup first.

To localize strings in Python files, import either gettext_lazy or ugettext
from this module as _, then use _('foo') to mark the strings to be translated.
Use gettext_lazy for strings that are declared before a language has been
selected; ugettext for those after (ugettext is safe to use in all Handlers)."""

__author__ = 'kpy@google.com (Ka-Ping Yee)'

import django
import django.conf
import django.template
import django.template.loaders.base
import django.utils.translation
import os
from django.utils.translation import activate, gettext_lazy, ugettext

LANGUAGE_CODE = 'en'
LANGUAGES_BIDI = ['ar', 'he', 'fa', 'iw', 'ur']

if os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
    # See https://web.archive.org/web/20160916120959/http://code.google.com/p/googleappengine/issues/detail?id=985
    import urllib
    urllib.getproxies_macosx_sysconf = lambda: {}

django.conf.settings.configure()
django.conf.settings.LANGUAGE_CODE = LANGUAGE_CODE
# Enables Django translation system e.g. {% trans %} tag
django.conf.settings.USE_I18N = True
# Enables localized formatting
# e.g. localizing date/time format for {% my_date|date:"DATETIME_FORMAT" %}
django.conf.settings.USE_L10N = True
django.conf.settings.LOCALE_PATHS = ('locale',)
django.conf.settings.LANGUAGES_BIDI = LANGUAGES_BIDI

# https://docs.djangoproject.com/en/1.9/ref/templates/upgrading/#the-templates-settings
django.conf.settings.TEMPLATES = [
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
                'django_setup.TemplateLoader',
            ]
        },
    },
]

# It's required to call this function when we use Django features outside
# Django framework.
django.setup()


class TemplateLoader(django.template.loaders.base.Loader):
    """Our custom template loader, which loads templates from Resources."""

    def get_template(self, name, template_dirs=None, skip=None):
        import resources
        lang = django.utils.translation.get_language()  # currently active lang
        resource = resources.get_localized(name, lang)
        template = resource and resource.get_template()
        if template:
            return template
        else:
            raise django.template.TemplateDoesNotExist(name)

    def get_contents(self, origin):
        # Defining this method is necessary so that Django recognizes that
        # this loader is in the new format (using get_template() instead of
        # load_template()). But this method is actually not called when
        # get_template() is overridden.
        raise Exception('Not expected to be called')
