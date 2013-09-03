#!/usr/bin/python2.5
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

import django.conf
import django.template
import django.template.loader
import django.utils.translation
import os
from django.utils.translation import activate, gettext_lazy, ugettext

LANGUAGE_CODE = 'en'
LANGUAGES_BIDI = ['ar', 'he', 'fa', 'iw', 'ur']

if os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
    # See http://code.google.com/p/googleappengine/issues/detail?id=985
    import urllib
    urllib.getproxies_macosx_sysconf = lambda: {}

try:
    django.conf.settings.configure()
except:
    pass
django.conf.settings.LANGUAGE_CODE = LANGUAGE_CODE
# Enables Django translation system e.g. {% trans %} tag
django.conf.settings.USE_I18N = True
# Enables localized formatting
# e.g. localizing date/time format for {% my_date|date:"DATETIME_FORMAT" %}
django.conf.settings.USE_L10N = True
django.conf.settings.LOCALE_PATHS = ('locale',)
django.conf.settings.LANGUAGES_BIDI = LANGUAGES_BIDI
django.conf.settings.TEMPLATE_LOADERS = ('django_setup.TemplateLoader',)


class TemplateLoader(django.template.loader.BaseLoader):
    """Our custom template loader, which loads templates from Resources."""
    is_usable = True  # Django requires this flag

    def load_template(self, name, dirs):
        import resources
        lang = django.utils.translation.get_language()  # currently active lang
        resource = resources.get_localized(name, lang)
        template = resource and resource.get_template()
        if template:
            return template, name + ':' + lang
        else:
            raise django.template.TemplateDoesNotExist(name)

    def load_template_source(self, name, dirs):
        # Silly Django requires custom TemplateLoaders to have this method,
        # but the framework actually only calls load_template().
        pass
