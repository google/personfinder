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

__author__ = 'kpy@google.com (Ka-Ping Yee) and many other Googlers'

import cgi
from datetime import datetime
import httplib
import logging
import model
import os
import pfif
import re
import time
import traceback
import urllib
import urlparse

import django.conf
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import webapp
import google.appengine.ext.webapp.template
import google.appengine.ext.webapp.util

import config
import template_fix


ROOT = os.path.abspath(os.path.dirname(__file__))


# ==== Localization setup ======================================================

try:
    django.conf.settings.configure()
except:
    pass
django.conf.settings.LANGUAGE_CODE = 'en'
django.conf.settings.USE_I18N = True
django.conf.settings.LOCALE_PATHS = (os.path.join(ROOT, 'locale'),)
django.conf.settings.LANGUAGES_BIDI = ['ar', 'he', 'fa', 'iw', 'ur']

import django.utils.translation
# We use lazy translation in this file because the locale isn't set until the
# Handler is initialized.
from django.utils.translation import gettext_lazy as _

# Mapping from language codes to endonyms for all available languages.
LANGUAGE_ENDONYMS = {
    'ar': u'\u0627\u0644\u0639\u0631\u0628\u064A\u0629',  # Arabic
    'bg':  # Bulgarian
            u'\u0431\u044A\u043B\u0433\u0430\u0440\u0441\u043A\u0438',
    'ca': u'Catal\u00E0',  # Catalan
    'cs': u'\u010De\u0161tina',  # Czech
    'da': u'Dansk',  # Danish
    'el': u'\u0395\u03BB\u03BB\u03B7\u03BD\u03B9\u03BA\u03AC',  # Greek
    'en': u'English',  # English
    'en-GB': u'English (UK)',
    'es': u'Espa\u00F1ol',  # Spanish
    'eu': u'euskara',  # Basque
    'fa': u'\u0641\u0627\u0631\u0633\u06CC',  # Persian
    'fi': u'suomi',  # Finnish
    'fil': u'Filipino',  # Filipino
    'fr': u'Fran\u00e7ais',  # French
    'fr-CA': u'Fran\u00e7ais (Canada)',  # Canadian French
    'gl': u'Galego',  # Galician
    'hi': u'\u0939\u093F\u0928\u094D\u0926\u0940',  # Hindi
    'hr': u'Hrvatski',  # Croatian
    'ht': u'Krey\u00f2l',  # Kreyol
    'hu': u'magyar',  # Hungarian
    'id': u'Bahasa Indonesia',  # Indonesian
    'he': u'\u05E2\u05D1\u05E8\u05D9\u05EA',  # Hebrew
    'ja': u'\u65E5\u672C\u8A9E',  # Japanese
    'ko': u'\uD55C\uAD6D\uC5B4',  # Korean
    'lt': u'Latvie\u0161u valoda',  # Latvian
    'nl': u'Nederlands',  # Dutch
    'no': u'Norsk',  # Norwegian
    'pl': u'polski',  # Polish
    'pt-PT': u'Portugu\u00EAs',  # Portuguese (Portugal)
    'ro': u'Rom\u00E2n\u0103',  # Romanian
    'ru': u'\u0420\u0443\u0441\u0441\u043A\u0438\u0439',  # Russian
    'sk': u'Sloven\u010Dina',  # Slovak
    'sl': u'Sloven\u0161\u010Dina',  # Slovenian
    'sr': u'\u0441\u0440\u043F\u0441\u043A\u0438',  # Serbian
    'sv': u'Svenska',  # Swedish
    'th': u'\u0E44\u0E17\u0E22',  # Thai
    'tr': u'T\u00FCrk\u00E7e',  # Turkish
    'uk':  # Ukranian
            u'\u0423\u043A\u0440\u0430\u0457\u043D\u0441\u044C\u043A\u0430',
    'ur': u'\u0627\u0631\u062F\u0648',  # Urdu
    'vi': u'Ti\u1EBFng Vi\u1EC7t',  # Vietnamese
    'zh-TW': u'\u4E2D \u6587 (\u7E41 \u9AD4)',  # Chinese (Traditional)
    'zh-CN': u'\u4E2D \u6587 (\u7B80 \u4F53)',  # Chinese (Simplified)
}

# Mapping from language codes to the names of LayoutCode constants.  See:
# http://code.google.com/apis/ajaxlanguage/documentation/referenceKeyboard.html
VIRTUAL_KEYBOARD_LAYOUTS = {
    'ur': 'URDU'
}


# ==== Field value text ========================================================

# UI text for the sex field when displaying a person.
PERSON_SEX_TEXT = {
    # This dictionary must have an entry for '' that gives the default text.
    '': '',
    'female': _('female'),
    'male': _('male'),
    'other': _('other')
}

assert set(PERSON_SEX_TEXT.keys()) == set(pfif.PERSON_SEX_VALUES)

def get_person_sex_text(person):
    """Returns the UI text for a person's sex field."""
    return PERSON_SEX_TEXT.get(person.sex or '')

# UI text for the status field when posting or displaying a note.
NOTE_STATUS_TEXT = {
    # This dictionary must have an entry for '' that gives the default text.
    '': _('Unspecified'),
    'information_sought': _('I am seeking information'),
    'is_note_author': _('I am this person'),
    'believed_alive':
        _('I have received information that this person is alive'),
    'believed_missing': _('I have reason to think this person is missing'),
    'believed_dead': _('I have received information that this person is dead'),
}

assert set(NOTE_STATUS_TEXT.keys()) == set(pfif.NOTE_STATUS_VALUES)

def get_note_status_text(note):
    """Returns the UI text for a note's status field."""
    return NOTE_STATUS_TEXT.get(note.status or '')


# UI text for the rolled-up status when displaying a person.
# This is intended for the results page; it's not yet used but the strings
# are in here so we can get the translations started.
PERSON_STATUS_TEXT = {
    # This dictionary must have an entry for '' that gives the default text.
    '': _('Unspecified'),
    'information_sought': _('Someone is seeking information'),
    'is_note_author': _('This person has posted a message'),
    'believed_alive':
        _('Someone has received information that this person is alive'),
    'believed_missing': _('Someone has reported that this person is missing'),
    'believed_dead':
        _('Someone has received information that this person is dead'),
}

assert set(PERSON_STATUS_TEXT.keys()) == set(pfif.NOTE_STATUS_VALUES)


# ==== String formatting =======================================================

def format_utc_datetime(dt):
    if dt is None:
        return ''
    integer_dt = datetime(
        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    return integer_dt.isoformat() + 'Z'

def format_sitemaps_datetime(dt):
    integer_dt = datetime(
        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    return integer_dt.isoformat() + '+00:00'

def to_utf8(string):
    """If Unicode, encode to UTF-8; if 8-bit string, leave unchanged."""
    if isinstance(string, unicode):
        string = string.encode('utf-8')
    return string

def urlencode(params):
    """Apply UTF-8 encoding to any Unicode strings in the parameter dict.
    Leave 8-bit strings alone.  (urllib.urlencode doesn't support Unicode.)"""
    keys = params.keys()
    keys.sort()  # Sort the keys to get canonical ordering
    return urllib.urlencode([
        (to_utf8(key), to_utf8(params[key]))
        for key in keys if isinstance(params[key], basestring)])

def set_url_param(url, param, value):
    """This modifies a URL, setting the given param to the specified value.  This
    may add the param or override an existing value, or, if the value is None,
    it will remove the param.  Note that value must be a basestring and can't be
    an int, for example."""
    url_parts = list(urlparse.urlparse(url))
    params = dict(cgi.parse_qsl(url_parts[4]))
    if value is None:
        if param in params:
            del(params[param])
    else:
        params[param] = value
    url_parts[4] = urlencode(params)
    return urlparse.urlunparse(url_parts)


# ==== Validators ==============================================================

# These validator functions are used to check and parse query parameters.
# When a query parameter is missing or invalid, the validator returns a
# default value.  For parameter types with a false value, the default is the
# false value.  For types with no false value, the default is None.

def strip(string):
    return string.strip()

def validate_yes(string):
    return (string.strip().lower() == 'yes') and 'yes' or ''

def validate_role(string):
    return (string.strip().lower() == 'provide') and 'provide' or 'seek'

def validate_int(string):
    return string and int(string.strip())

def validate_sex(string):
    """Validates the 'sex' parameter, returning a canonical value or ''."""
    if string:
        string = string.strip().lower()
    return string in pfif.PERSON_SEX_VALUES and string or ''

APPROXIMATE_DATE_RE = re.compile(r'^\d{4}(-\d\d)?(-\d\d)?$')

def validate_approximate_date(string):
    if string:
        string = string.strip()
        if APPROXIMATE_DATE_RE.match(string):
            return string
    return ''

AGE_RE = re.compile(r'^\d+(-\d+)?$')

def validate_age(string):
    """Validates the 'age' parameter, returning a canonical value or ''."""
    if string:
        string = string.strip()
        if AGE_RE.match(string):
            return string
    return ''

def validate_status(string):
    """Validates an incoming status parameter, returning one of the canonical
    status strings or ''.  Note that '' is always used as the Python value
    to represent the 'unspecified' status."""
    if string:
        string = string.strip().lower()
    return string in pfif.NOTE_STATUS_VALUES and string or ''

DATETIME_RE = re.compile(r'^(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z$')

def validate_datetime(string):
    if not string:
        return None  # A missing value is okay.
    match = DATETIME_RE.match(string)
    if match:
        return datetime(*map(int, match.groups()))
    raise ValueError('Bad datetime: %r' % string)

def validate_image(bytestring):
    try:
        image = ''
        if bytestring:
            image = images.Image(bytestring)
            image.width
        return image
    except:
        return False


# ==== Other utilities =========================================================

def filter_sensitive_fields(records, request=None):
    """Removes sensitive fields from a list of dictionaries."""
    for record in records:
        if 'date_of_birth' in record:
            record['date_of_birth'] = ''
        if 'author_email' in record:
            record['author_email'] = ''
        if 'author_phone' in record:
            record['author_phone'] = ''
        if 'email_of_found_person' in record:
            record['email_of_found_person'] = ''
        if 'phone_of_found_person' in record:
            record['phone_of_found_person'] = ''

def get_secret(name):
    """Gets a secret from the datastore by name, or returns None if missing."""
    secret = model.Secret.get_by_key_name(name)
    if secret:
        return secret.secret


# ==== Base Handler ============================================================

class Struct:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

global_cache = {}
global_cache_insert_time = {}


class Handler(webapp.RequestHandler):
    auto_params = {
        'lang': strip,
        'query': strip,
        'first_name': strip,
        'last_name': strip,
        'sex': validate_sex,
        'date_of_birth': validate_approximate_date,
        'age': validate_age,
        'home_street': strip,
        'home_neighborhood': strip,
        'home_city': strip,
        'home_state': strip,
        'home_postal_code': strip,
        'home_country': strip,
        'author_name': strip,
        'author_phone': strip,
        'author_email': strip,
        'source_url': strip,
        'source_date': strip,
        'source_name': strip,
        'description': strip,
        'dupe_notes': validate_yes,
        'id': strip,
        'text': strip,
        'status': validate_status,
        'last_known_location': strip,
        'found': validate_yes,
        'email_of_found_person': strip,
        'phone_of_found_person': strip,
        'error': strip,
        'role': validate_role,
        'clone': validate_yes,
        'small': validate_yes,
        'style': strip,
        'add_note': validate_yes,
        'photo_url': strip,
        'photo': validate_image,
        'max_results': validate_int,
        'skip': validate_int,
        'min_entry_date': validate_datetime,
        'person_record_id': strip,
        'omit_notes': validate_yes,
        'id1': strip,
        'id2': strip,
        'id3': strip,
        'version': strip,
        'content_id': strip,
        'target': strip,
        'signature': strip,
        'flush_cache': validate_yes,
        'operation': strip,
        'confirm': validate_yes
    }

    def redirect(self, url, **params):
        if re.match('^[a-z]+:', url):
            if params:
                url += '?' + urlencode(params)
        else:
            url = self.get_url(url, **params)
        return webapp.RequestHandler.redirect(self, url)

    def cache_key_for_request(self):
        # Use the whole url as the key.  We make sure the lang is included or
        # the old language may be sticky.
        return set_url_param(self.request.url, 'lang', self.params.lang)

    def render_from_cache(self, cache_time, key=None):
        """Render from cache if appropriate. Returns true if done."""
        if not cache_time:
            return False

        now = time.time()
        key = self.cache_key_for_request()
        if cache_time > (now - global_cache_insert_time.get(key, 0)):
            self.write(global_cache[key])
            logging.debug('Rendering cached response.')
            return True
        logging.debug('Render cache missing/stale, re-rendering.')
        return False

    def render(self, name, cache_time=0, **values):
        """Render the template, optionally caching locally.

        The optional cache is local instead of memcache--this is faster but
        will be recomputed for every running instance.  It also consumes local
        memory, but that's not a likely issue for likely amounts of cached data.

        Args:
            name: name of the file in the template directory.
            cache_time: optional time in seconds to cache the response locally.
        """
        if self.render_from_cache(cache_time):
            return
        values['env'] = self.env  # pass along application-wide context
        values['params'] = self.params  # pass along the query parameters
        response = webapp.template.render(os.path.join(ROOT, name), values)
        self.write(response)
        if cache_time:
            now = time.time()
            key = self.cache_key_for_request()
            global_cache[key] = response
            global_cache_insert_time[key] = now

    def error(self, code, message=''):
        webapp.RequestHandler.error(self, code)
        if not message:
            message = 'Error %d: %s' % (code, httplib.responses.get(code))
        self.render('templates/error.html', message=message)

    def write(self, text):
        self.response.out.write(text)

    def select_locale(self):
        """Detect and activate the appropriate locale.  The 'lang' query
        parameter has priority, then the django_language cookie, then the
        default setting."""
        lang = (self.params.lang or
                self.request.cookies.get('django_language', None) or
                django.conf.settings.LANGUAGE_CODE)
        self.response.headers.add_header(
            'Set-Cookie', 'django_language=%s' % lang)
        django.utils.translation.activate(lang)
        rtl = django.utils.translation.get_language_bidi()
        self.response.headers.add_header('Content-Language', lang)
        return lang, rtl

    def get_url(self, path, **params):
        """Constructs the absolute URL for a given path and query parameters,
        preserving the current 'subdomain', 'small', and 'style' parameters."""
        for name in ['subdomain', 'small', 'style']:
            if self.request.get(name):
                params[name] = self.request.get(name)
        if params:
            path += ('?' in path and '&' or '?') + urlencode(params)
        scheme, netloc, _, _, _ = urlparse.urlsplit(self.request.url)
        return scheme + '://' + netloc + path

    def handle_exception(self, exception, debug_mode):
        logging.error(traceback.format_exc())
        self.response.set_status(500)
        return self.render('templates/error.html', message=_(
            'There was an error processing your request.  Sorry for the '
            'inconvenience.  Our administrators will investigate the source '
            'of the problem, but please check that the format of your '
            'request is correct.'))

    def initialize(self, *args):
        webapp.RequestHandler.initialize(self, *args)
        self.params = Struct()
        self.env = Struct()

        # Log AppEngine-specific request headers.
        for name in self.request.headers.keys():
            if name.lower().startswith('x-appengine'):
                logging.debug('%s: %s' % (name, self.request.headers[name]))

        # Validate query parameters.
        for name, validator in self.auto_params.items():
            try:
                value = self.request.get(name, '')
                setattr(self.params, name, validator(value))
            except Exception, e:
                # There's no way to gracefully abort here; the best we can do
                # is to send an error message and stop sending any more output.
                self.error(400, 'Invalid query parameter %s: %s' % (name, e))
                self.response.out.write = lambda *args: None
                setattr(self.params, name, validator(None))

        if self.params.flush_cache:
            # Useful for debugging and testing.
            memcache.flush_all()
            global_cache.clear()
            global_cache_insert_time.clear()

        # Determine the subdomain.
        self.subdomain = ''
        levels = self.request.headers.get('Host', '').split('.')
        if levels[-2:] == ['appspot', 'com'] and len(levels) >= 4:
            # foo.person-finder.appspot.com -> subdomain 'foo'
            # bar.kpy.latest.person-finder.appspot.com -> subdomain 'bar'
            self.subdomain = levels[0]
        # The 'subdomain' query parameter always overrides the hostname.
        self.subdomain = self.request.get('subdomain', self.subdomain)
        if not self.subdomain:
            return self.error(400, 'No subdomain specified.')

        # To preserve the subdomain properly as the user navigates the site:
        # (a) For links, always use self.get_url to get the URL for the HREF.
        # (b) For forms, use a plain path like "/view" for the ACTION and
        #     include {{env.subdomain_field}} inside the form element.
        subdomain_field = (
            '<input type="hidden" name="subdomain" value="%s">' %
            self.request.get('subdomain', ''))

        # Activate localization.
        lang, rtl = self.select_locale()

        # Put commonly used template variables in self.env.
        self.config = config.Configuration(self.subdomain)
        self.env.subdomain_title = self.config.subdomain_title.get(
            lang, self.config.subdomain_title['en'])
        self.env.keywords = self.config.keywords
        self.env.family_name_first = self.config.family_name_first
        self.env.use_family_name = self.config.use_family_name
        self.env.use_postal_code = self.config.use_postal_code
        self.env.map_default_zoom = self.config.map_default_zoom
        self.env.map_default_center = self.config.map_default_center
        self.env.map_size_pixels = self.config.map_size_pixels
        self.env.lang = lang
        self.env.virtual_keyboard_layout = VIRTUAL_KEYBOARD_LAYOUTS.get(lang)
        self.env.rtl = rtl
        self.env.back_chevron = rtl and u'\xbb' or u'\xab'
        self.env.analytics_id = get_secret('analytics_id')
        self.env.maps_api_key = get_secret('maps_api_key')
        self.env.subdomain_field = subdomain_field
        self.env.main_url = self.get_url('/')
        self.env.embed_url = self.get_url('/embed')
        self.env.developers_url = self.get_url('/developers')

        # Provide the contents of the language menu.
        self.env.language_menu = [
            {'lang': lang,
             'endonym': LANGUAGE_ENDONYMS[lang],
             'url': set_url_param(self.request.url, 'lang', lang)}
            for lang in self.config.language_menu_options
        ]

        # Provide the domain of the current request.
        self.env.netloc = urlparse.urlparse(self.request.url)[1]
        self.env.domain = self.env.netloc.split(':')[0]

        # Provide the status field values for templates.
        self.env.statuses = [Struct(value=value, text=NOTE_STATUS_TEXT[value])
                             for value in pfif.NOTE_STATUS_VALUES]

def run(*mappings, **kwargs):
    webapp.util.run_wsgi_app(webapp.WSGIApplication(list(mappings), **kwargs))
