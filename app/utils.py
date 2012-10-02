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

from django_setup import ugettext as _  # always keep this first

import calendar
import cgi
from datetime import datetime, timedelta
import httplib
import logging
import os
import random
import re
import sys
import time
import traceback
import unicodedata
import urllib
import urlparse

import django.utils.html
from google.appengine.api import images
from google.appengine.api import mail
from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.ext import webapp
import google.appengine.ext.webapp.template
import google.appengine.ext.webapp.util
from recaptcha.client import captcha

import const
import config
import legacy_redirect
import model
import pfif
import resources
import user_agents

# The domain name from which to send e-mail.
EMAIL_DOMAIN = 'appspotmail.com'  # All apps on appspot.com use this for mail.

# Query parameters which are automatically preserved on page transition
# if you use utils.BaseHandler.get_url() or
# env.hidden_input_tags_for_preserved_query_params.
PRESERVED_QUERY_PARAM_NAMES = ['ui', 'charsets']


# ==== Field value text ========================================================

def get_person_sex_text(person):
    """Returns the UI text for a person's sex field."""
    return const.PERSON_SEX_TEXT.get(person.sex or '')

def get_note_status_text(note):
    """Returns the UI text for a note's status field."""
    return const.NOTE_STATUS_TEXT.get(note.status or '')

def get_person_status_text(person):
    """Returns the UI text for a person's latest_status."""
    return const.PERSON_STATUS_TEXT.get(person.latest_status or '')

# Things that occur as prefixes of global paths (i.e. no repository name).
GLOBAL_PATH_RE = re.compile(r'^/(global|personfinder)(/?|/.*)$')


# ==== String formatting =======================================================

def format_boolean(value):
    return value and 'true' or 'false'

def format_utc_datetime(dt):
    if not dt:
        return ''
    return dt.replace(microsecond=0).isoformat() + 'Z'

def format_utc_timestamp(timestamp):
    if not isinstance(timestamp, (int, float)):
        return ''
    return format_utc_datetime(datetime.utcfromtimestamp(timestamp))

def format_sitemaps_datetime(dt):
    integer_dt = datetime(
        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    return integer_dt.isoformat() + '+00:00'

def encode(string, encoding='utf-8'):
    """If unicode, encode to encoding; if 8-bit string, leave unchanged."""
    if isinstance(string, unicode):
        string = string.encode(encoding)
    return string

def urlencode(params, encoding='utf-8'):
    """Encode the key-value pairs in 'params' into a query string, applying
    the specified encoding to any Unicode strings and ignoring any keys that
    have value == None.  (urllib.urlencode doesn't support Unicode)."""
    keys = params.keys()
    keys.sort()  # Sort the keys to get canonical ordering
    return urllib.urlencode([
        (encode(key, encoding), encode(params[key], encoding))
        for key in keys if isinstance(params[key], basestring)])

def set_param(params, param, value):
    """Take the params from a urlparse and override one of the values."""
    # This will strip out None-valued params and collapse repeated params.
    params = dict(cgi.parse_qsl(params))
    if value is None:
        if param in params:
            del(params[param])
    else:
        params[param] = value
    return urlencode(params)


def set_url_param(url, param, value):
    """This modifies a URL setting the given param to the specified value.  This
    may add the param or override an existing value, or, if the value is None,
    it will remove the param.  Note that value must be a basestring and can't be
    an int, for example."""
    url_parts = list(urlparse.urlparse(url))
    url_parts[4] = set_param(url_parts[4], param, value)
    return urlparse.urlunparse(url_parts)

def anchor_start(href):
    """Returns the HREF escaped and embedded in an anchor tag."""
    return '<a href="%s">' % django.utils.html.escape(href)

def anchor(href, body):
    """Returns a string anchor HTML element with the given href and body."""
    return anchor_start(href) + django.utils.html.escape(body) + '</a>'


# ==== Validators ==============================================================

# These validator functions are used to check and parse query parameters.
# Each validator should return a parsed, sanitized value, or return a default
# value, or raise ValueError to display an error message to the user.

def strip(string):
    # Trailing nulls appear in some strange character encodings like Shift-JIS.
    return string.strip().rstrip('\0')

def strip_and_lower(string):
    return strip(string).lower()

def validate_yes(string):
    return (strip(string).lower() == 'yes') and 'yes' or ''

def validate_checkbox(string):
    return (strip(string).lower() == 'on') and 'yes' or ''

def validate_role(string):
    return (strip(string).lower() == 'provide') and 'provide' or 'seek'

def validate_int(string):
    return string and int(strip(string))

def validate_sex(string):
    """Validates the 'sex' parameter, returning a canonical value or ''."""
    if string:
        string = strip(string).lower()
    return string in pfif.PERSON_SEX_VALUES and string or ''

def validate_expiry(value):
    """Validates that the 'expiry_option' parameter is a positive integer.

    Returns:
      the int() value if it's present and parses, or the default_expiry_days
      for the repository, if it's set, otherwise -1 which represents the
      'unspecified' status.
    """
    try:
        value = int(value)
    except Exception, e:
        return None
    return value > 0 and value or None

APPROXIMATE_DATE_RE = re.compile(r'^\d{4}(-\d\d)?(-\d\d)?$')

def validate_approximate_date(string):
    if string:
        string = strip(string)
        if APPROXIMATE_DATE_RE.match(string):
            return string
    return ''

AGE_RE = re.compile(r'^\d+(-\d+)?$')
# Hyphen with possibly surrounding whitespaces.
HYPHEN_RE = re.compile(
    ur'\s*[-\u2010-\u2015\u2212\u301c\u30fc\ufe58\ufe63\uff0d]\s*',
    re.UNICODE)

def validate_age(string):
    """Validates the 'age' parameter, returning a canonical value or ''."""
    if string:
        string = strip(string)
        string = unicodedata.normalize('NFKC', unicode(string))
        string = HYPHEN_RE.sub('-', string)
        if AGE_RE.match(string):
            return string
    return ''

def validate_status(string):
    """Validates an incoming status parameter, returning one of the canonical
    status strings or ''.  Note that '' is always used as the Python value
    to represent the 'unspecified' status."""
    if string:
        string = strip(string).lower()
    return string in pfif.NOTE_STATUS_VALUES and string or ''

DATETIME_RE = re.compile(r'^(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z$')

def validate_datetime(string):
    if not string:
        return None  # A missing value is okay.
    match = DATETIME_RE.match(string)
    if match:
        return datetime(*map(int, match.groups()))
    raise ValueError('Bad datetime: %r' % string)

def validate_timestamp(string):
    try:
        return string and datetime.utcfromtimestamp(float(strip(string)))
    except:
        raise ValueError('Bad timestamp: %s' % string)

def validate_image(bytestring):
    try:
        image = None
        if bytestring:
            image = images.Image(bytestring)
            image.width
        return image
    except:
        return False

def validate_version(string):
    """Version, if present, should be in pfif versions."""
    if string and strip(string) not in pfif.PFIF_VERSIONS:
        raise ValueError('Bad pfif version: %s' % string)
    return pfif.PFIF_VERSIONS[strip(string) or pfif.PFIF_DEFAULT_VERSION]

REPO_RE = re.compile('^[a-z0-9-]+$')

def validate_repo(string):
    string = (string or '').strip()
    if not string:
        return None
    if string == 'global':
        raise ValueError('"global" is an illegal repository name.')
    if REPO_RE.match(string):
        return string
    raise ValueError('Repository names can only contain '
                     'lowercase letters, digits, and hyphens.')


RESOURCE_NAME_RE = re.compile('^[a-z0-9._-]+$')

def validate_resource_name(string):
    """A resource name or bundle label."""
    string = (string or '').strip().lower()
    if not string:
        return None
    if RESOURCE_NAME_RE.match(string):
        return string
    raise ValueError('Invalid resource name or bundle name: %r' % string)


LANG_RE = re.compile('^[A-Za-z0-9-]+$')

def validate_lang(string):
    """A BCP 47 language tag."""
    string = (string or '').strip().lower()
    if not string:
        return None
    if LANG_RE.match(string):
        return string
    raise ValueError('Invalid language tag: %r' % string)


def validate_cache_seconds(string):
    """A number of seconds to cache a Resource in RAM."""
    string = (string or '').strip()
    if string:
        return float(string)
    return 1.0


# ==== Other utilities =========================================================

def url_is_safe(url):
    current_scheme, _, _, _, _ = urlparse.urlsplit(url)
    return current_scheme in ['http', 'https']

def get_app_name():
    """Canonical name of the app, without HR s~ nonsense.  This only works in
    the context of the appserver (eg remote_api can't use it)."""
    from google.appengine.api import app_identity
    return app_identity.get_application_id()

def sanitize_urls(record):
    """Clean up URLs to protect against XSS."""
    # Single-line URLs.
    for field in ['photo_url', 'source_url']:
        url = getattr(record, field, None)
        if url and not url_is_safe(url):
            setattr(record, field, None)
    # Multi-line URLs.
    for field in ['profile_urls']:
        urls = (getattr(record, field, None) or '').splitlines()
        sanitized_urls = [url for url in urls if url and url_is_safe(url)]
        if len(urls) != len(sanitized_urls):
            setattr(record, field, '\n'.join(sanitized_urls))

def get_host(host=None):
    host = host or os.environ['HTTP_HOST']
    """Return the host name, without version specific details."""
    parts = host.split('.')
    if len(parts) > 3:
        return '.'.join(parts[-3:])
    else:
        return host

def optionally_filter_sensitive_fields(records, auth=None):
    """Removes sensitive fields from a list of dictionaries, unless the client
    has full read authorization."""
    if not (auth and auth.full_read_permission):
        filter_sensitive_fields(records)

def filter_sensitive_fields(records):
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

# The current time for testing as a datetime object, or None if using real time.
_utcnow_for_test = None

def set_utcnow_for_test(now):
    """Sets the current time for testing purposes.  Pass in a datetime object
    or a timestamp in epoch seconds; or pass None to revert to real time."""
    global _utcnow_for_test
    if isinstance(now, (int, float)):
        now = datetime.utcfromtimestamp(float(now))
    _utcnow_for_test = now

def get_utcnow():
    """Returns the current UTC datetime (settable with set_utcnow_for_test)."""
    global _utcnow_for_test
    return (_utcnow_for_test is None) and datetime.utcnow() or _utcnow_for_test

def get_timestamp(dt):
    """Converts datetime object to a float value in epoch seconds."""
    return calendar.timegm(dt.utctimetuple()) + dt.microsecond * 1e-6

def get_utcnow_timestamp():
    """Returns the current time in epoch seconds (settable with
    set_utcnow_for_test)."""
    return get_timestamp(get_utcnow())

def log_api_action(handler, action, num_person_records=0, num_note_records=0,
                   people_skipped=0, notes_skipped=0):
    """Log an API action."""
    if handler.config and handler.config.api_action_logging:
        model.ApiActionLog.record_action(
            handler.repo, handler.params.key,
            handler.params.version.version, action,
            num_person_records, num_note_records,
            people_skipped, notes_skipped,
            handler.request.headers.get('User-Agent'),
            handler.request.remote_addr, handler.request.url)

def get_full_name(given_name, family_name, config):
    """Return full name string obtained by concatenating given_name and
    family_name in the order specified by config.family_name_first, or just
    given_name if config.use_family_name is False."""
    if config.use_family_name:
        separator = (given_name and family_name) and u' ' or u''
        if config.family_name_first:
            return separator.join([family_name, given_name])
        else:
            return separator.join([given_name, family_name])
    else:
        return given_name

def get_person_full_name(person, config):
    """Return person's full name.  "person" can be any object with "given_name"
    and "family_name" attributes."""
    return get_full_name(person.given_name, person.family_name, config)

def send_confirmation_email_to_record_author(
    handler, person, action, confirm_url, record_id):
    """Send the author an email to confirm enabling/disabling notes
    of a record."""
    if not person.author_email:
        return handler.error(
            400, _('No author email for record %(id)s.') % {'id' : record_id})

    # i18n: Subject line of an e-mail message confirming the author
    # wants to disable notes for this record
    params = {
        'given_name': person.given_name,
        'family_name': person.family_name,
    }
    if action == 'enable':
        subject = _(
            '[Person Finder] Enable notes on '
            '"%(given_name)s %(family_name)s"?'
            ) % params
    elif action == 'disable':
        subject = _(
            '[Person Finder] Disable notes on '
            '"%(given_name)s %(family_name)s"?'
            ) % params
    else:
        raise ValueError('Unknown action: %s' % action)
        

    # send e-mail to record author confirming the lock of this record.
    template_name = '%s_notes_email.txt' % action
    handler.send_mail(
        subject=subject,
        to=person.author_email,
        body=handler.render_to_string(
            template_name,
            author_name=person.author_name,
            given_name=person.given_name,
            family_name=person.family_name,
            site_url=handler.get_url('/'),
            confirm_url=confirm_url
        )
    )

def get_repo_url(request, repo, scheme=None):
    """Constructs the absolute root URL for a given repository."""
    req_scheme, req_netloc, req_path, _, _ = urlparse.urlsplit(request.url)
    prefix = req_path.startswith('/personfinder') and '/personfinder' or ''
    if req_netloc.split(':')[0] == 'localhost':
        scheme = 'http'  # HTTPS is not available when using dev_appserver
    return (scheme or req_scheme) + '://' + req_netloc + prefix + '/' + repo

def get_url(request, repo, action, charset='utf-8', scheme=None, **params):
    """Constructs the absolute URL for a given action and query parameters,
    preserving the current repo and the parameters listed in
    PRESERVED_QUERY_PARAM_NAMES."""
    repo_url = get_repo_url(request, repo or 'global', scheme)
    for name in PRESERVED_QUERY_PARAM_NAMES:
        params[name] = params.get(name, request.get(name, None))
    query = urlencode(params, charset)
    return repo_url + '/' + action.lstrip('/') + (query and '?' + query or '')

def add_profile_icon_url(website, handler):
    website['icon_url'] = \
        handler.env.global_url + '/' + website['icon_filename']
    return website


# ==== Struct ==================================================================

class Struct:
    """A simple bag of attributes."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def get(self, name, default=None):
        return self.__dict__.get(name, default)


# ==== Base Handler ============================================================

class BaseHandler(webapp.RequestHandler):
    # Handlers that don't need a repository name can set this to False.
    repo_required = True

    # Handlers that require HTTPS can set this to True.
    https_required = False

    # Set this to True to enable a handler even for deactivated repositories.
    ignore_deactivation = False

    # List all accepted query parameters here with their associated validators.
    auto_params = {
        'add_note': validate_yes,
        'age': validate_age,
        'alternate_family_names': strip,
        'alternate_given_names': strip,
        'author_email': strip,
        'author_made_contact': validate_yes,
        'author_name': strip,
        'author_phone': strip,
        'cache_seconds': validate_cache_seconds,
        'clone': validate_yes,
        'confirm': validate_yes,
        'content_id': strip,
        'cursor': strip,
        'date_of_birth': validate_approximate_date,
        'description': strip,
        'dupe_notes': validate_yes,
        'email_of_found_person': strip,
        'error': strip,
        'expiry_option': validate_expiry,
        'family_name': strip,
        'given_name': strip,
        'home_city': strip,
        'home_country': strip,
        'home_neighborhood': strip,
        'home_postal_code': strip,
        'home_state': strip,
        'home_street': strip,
        'id': strip,
        'id1': strip,
        'id2': strip,
        'id3': strip,
        'key': strip,
        'lang': validate_lang,
        'last_known_location': strip,
        'max_results': validate_int,
        'min_entry_date': validate_datetime,
        'new_repo': validate_repo,
        'note_photo': validate_image,
        'note_photo_url': strip,
        'omit_notes': validate_yes,
        'operation': strip,
        'person_record_id': strip,
        'phone_of_found_person': strip,
        'photo': validate_image,
        'photo_url': strip,
        'profile_url1': strip,
        'profile_url2': strip,
        'profile_url3': strip,
        'query': strip,
        'resource_bundle': validate_resource_name,
        'resource_bundle_original': validate_resource_name,
        'resource_lang': validate_lang,
        'resource_name': validate_resource_name,
        'resource_set_preview': validate_yes,
        'role': validate_role,
        'sex': validate_sex,
        'signature': strip,
        'skip': validate_int,
        'small': validate_yes,
        'source_date': strip,
        'source_name': strip,
        'source_url': strip,
        'status': validate_status,
        'style': strip,
        'subscribe': validate_checkbox,
        'subscribe_email': strip,
        'suppress_redirect': validate_yes,
        'target': strip,
        'text': strip,
        'ui': strip_and_lower,
        'utcnow': validate_timestamp,
        'version': validate_version,
    }

    def maybe_redirect_jp_tier2_mobile(self):
        """Returns a redirection URL based on the jp_tier2_mobile_redirect_url
        setting if the request is from a Japanese Tier-2 phone."""
        if (self.config and
            self.config.jp_tier2_mobile_redirect_url and
            not self.params.suppress_redirect and
            self.env.ui != 'small' and
            user_agents.is_jp_tier2_mobile_phone(self.request)):
            redirect_url = (self.config.jp_tier2_mobile_redirect_url + '/' +
                    self.env.action)
            if self.request.query_string:
                redirect_url += '?' + self.request.query_string
            return redirect_url
        return ''

    def redirect(self, path, repo=None, permanent=False, **params):
        # This will prepend the repo to the path to create a working URL,
        # unless the path has a global prefix or is an absolute URL.
        if re.match('^[a-z]+:', path) or GLOBAL_PATH_RE.match(path):
            if params:
              path += '?' + urlencode(params, self.charset)
        else:
            path = self.get_url(path, repo, **params)
        return webapp.RequestHandler.redirect(self, path, permanent=permanent)

    def render(self, name, language_override=None, cache_seconds=0,
               get_vars=lambda: {}, **vars):
        """Renders a template to the output stream, passing in the variables
        specified in **vars as well as any additional variables returned by
        get_vars().  Since this is intended for use by a dynamic page handler,
        caching is off by default; if cache_seconds is positive, then
        get_vars() will be called only when cached content is unavailable."""
        self.write(self.render_to_string(
            name, language_override, cache_seconds, get_vars, **vars))

    def render_to_string(self, name, language_override=None, cache_seconds=0,
                         get_vars=lambda: {}, **vars):
        """Renders a template to a string, passing in the variables specified
        in **vars as well as any additional variables returned by get_vars().
        Since this is intended for use by a dynamic page handler, caching is
        off by default; if cache_seconds is positive, then get_vars() will be
        called only when cached content is unavailable."""
        # TODO(kpy): Make the contents of extra_key overridable by callers?
        lang = language_override or self.env.lang
        extra_key = (self.env.repo, self.env.charset, self.request.query_string)
        def get_all_vars():
            vars['env'] = self.env  # pass along application-wide context
            vars['config'] = self.config  # pass along the configuration
            vars['params'] = self.params  # pass along the query parameters
            vars.update(get_vars())
            return vars
        return resources.get_rendered(
            name, lang, extra_key, get_all_vars, cache_seconds)

    def error(self, code, message='', message_html=''):
        self.info(code, message, message_html, style='error')

    def info(self, code, message='', message_html='', style='info'):
        is_error = 400 <= code < 600
        if is_error:
            webapp.RequestHandler.error(self, code)
        else:
            self.response.set_status(code)
        if not message and not message_html:
            message = '%d: %s' % (code, httplib.responses.get(code))
        try:
            self.render('message.html', cls=style,
                        message=message, message_html=message_html)
        except:
            self.response.out.write(message + '<p>' + message_html)
        self.terminate_response()

    def terminate_response(self):
        """Prevents any further output from being written."""
        self.response.out.write = lambda *args: None
        self.get = lambda *args: None
        self.post = lambda *args: None

    def write(self, text):
        """Sends text to the client using the charset from select_charset()."""
        self.response.out.write(text.encode(self.env.charset, 'replace'))

    def get_url(self, action, repo=None, scheme=None, **params):
        """Constructs the absolute URL for a given action and query parameters,
        preserving the current repo and the parameters listed in
        PRESERVED_QUERY_PARAM_NAMES."""
        return get_url(self.request, repo or self.env.repo, action,
                       charset=self.env.charset, scheme=scheme, **params)

    @staticmethod
    def add_task_for_repo(repo, name, action, **kwargs):
        """Queues up a task for an individual repository."""
        task_name = '%s-%s-%s' % (repo, name, int(time.time()*1000))
        path = '/%s/%s' % (repo, action)
        taskqueue.add(name=task_name, method='GET', url=path, params=kwargs)

    def send_mail(self, to, subject, body):
        """Sends e-mail using a sender address that's allowed for this app."""
        app_id = get_app_name()
        sender = 'Do not reply <do-not-reply@%s.%s>' % (app_id, EMAIL_DOMAIN)
        logging.info('Add mail task: recipient %r, subject %r' % (to, subject))
        taskqueue.add(queue_name='send-mail', url='/global/admin/send_mail',
                      params={'sender': sender,
                              'to': to,
                              'subject': subject,
                              'body': body})

    def get_captcha_html(self, error_code=None, use_ssl=False):
        """Generates the necessary HTML to display a CAPTCHA validation box."""

        # We use the 'custom_translations' parameter for UI messages, whereas
        # the 'lang' parameter controls the language of the challenge itself.
        # reCAPTCHA falls back to 'en' if this parameter isn't recognized.
        lang = self.env.lang.split('-')[0]

        return captcha.get_display_html(
            public_key=config.get('captcha_public_key'),
            use_ssl=use_ssl, error=error_code, lang=lang,
            custom_translations={
                # reCAPTCHA doesn't support all languages, so we treat its
                # messages as part of this app's usual translation workflow
                'instructions_visual': _('Type the two words:'),
                'instructions_audio': _('Type what you hear:'),
                'play_again': _('Play the sound again'),
                'cant_hear_this': _('Download the sound as MP3'),
                'visual_challenge': _('Get a visual challenge'),
                'audio_challenge': _('Get an audio challenge'),
                'refresh_btn': _('Get a new challenge'),
                'help_btn': _('Help'),
                'incorrect_try_again': _('Incorrect.  Try again.')
            }
        )

    def get_captcha_response(self):
        """Returns an object containing the CAPTCHA response information for the
        given request's CAPTCHA field information."""
        challenge = self.request.get('recaptcha_challenge_field')
        response = self.request.get('recaptcha_response_field')
        remote_ip = os.environ['REMOTE_ADDR']
        return captcha.submit(
            challenge, response, config.get('captcha_private_key'), remote_ip)

    def handle_exception(self, exception, debug_mode):
        logging.error(traceback.format_exc())
        self.error(500, _(
            'There was an error processing your request.  Sorry for the '
            'inconvenience.  Our administrators will investigate the source '
            'of the problem, but please check that the format of your '
            'request is correct.'))

    def to_local_time(self, date):
        """Converts a datetime object to the local time configured for the
        current repository.  For convenience, returns None if date is None."""
        # TODO(kpy): This only works for repositories that have a single fixed
        # time zone offset and never use Daylight Saving Time.
        if date:
            if self.config.time_zone_offset:
                return date + timedelta(0, 3600*self.config.time_zone_offset)
            return date

    def initialize(self, request, response, env):
        webapp.RequestHandler.initialize(self, request, response)
        self.params = Struct()
        self.env = env
        self.repo = env.repo
        self.config = env.config
        self.charset = env.charset

        # Set default Content-Type header.
        self.response.headers['Content-Type'] = (
            'text/html; charset=%s' % self.charset)

        # Validate query parameters.
        for name, validator in self.auto_params.items():
            try:
                value = self.request.get(name, '')
                setattr(self.params, name, validator(value))
            except Exception, e:
                setattr(self.params, name, validator(None))
                return self.error(400, 'Invalid parameter %s: %s' % (name, e))

        # Log the User-Agent header.
        sample_rate = float(
            self.config and self.config.user_agent_sample_rate or 0)
        if random.random() < sample_rate:
            model.UserAgentLog(
                repo=self.repo, sample_rate=sample_rate,
                user_agent=self.request.headers.get('User-Agent'), lang=lang,
                accept_charset=self.request.headers.get('Accept-Charset', ''),
                ip_address=self.request.remote_addr).put()

        # Check for SSL (unless running on localhost for development).
        if self.https_required and self.env.domain != 'localhost':
            if self.env.scheme != 'https':
                return self.error(403, 'HTTPS is required.')

        # Check for an authorization key.
        self.auth = None
        if self.params.key:
            if self.repo:
                # check for domain specific one.
                self.auth = model.Authorization.get(self.repo, self.params.key)
            if not self.auth:
                # perhaps this is a global key ('*' for consistency with config).
                self.auth = model.Authorization.get('*', self.params.key)

        # Handlers that don't need a repository configuration can skip it.
        if not self.repo:
            if self.repo_required:
                return self.error(400, 'No repository specified.')
            return
        # Everything after this requires a repo.

        # Reject requests for repositories that don't exist.
        if not model.Repo.get_by_key_name(self.repo):
            if legacy_redirect.do_redirect(self):
                return legacy_redirect.redirect(self)
            html = 'No such repository. '
            if self.env.repo_options:
                html += 'Select:<p>' + self.render_to_string('repo-menu.html')
            return self.error(404, message_html=html)

        # If this repository has been deactivated, terminate with a message.
        if self.config.deactivated and not self.ignore_deactivation:
            self.env.language_menu = []
            self.env.robots_ok = True
            self.render('message.html', cls='deactivation',
                        message_html=self.config.deactivation_message_html)
            self.terminate_response()
