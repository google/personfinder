# Copyright 2017 Google Inc.
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

import calendar
import copy
from datetime import datetime, timedelta
import hmac
import httplib
import logging
import os
import random
import re
import string
import sys
import time
import traceback
import unicodedata
import urllib
import urlparse
import base64

from django.core.validators import EmailValidator, URLValidator, ValidationError
import django.utils.html
from django.utils.translation import ugettext as _
from django.template.defaulttags import register
from google.appengine.api import images
from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.ext import webapp
import google.appengine.ext.webapp.template
import google.appengine.ext.webapp.util
import recaptcha.client.captcha
from babel.dates import format_date
from babel.dates import format_datetime
from babel.dates import format_time
import babel

import const
import config
import model
import pfif
import resources

# The domain name from which to send e-mail.
EMAIL_DOMAIN = 'appspotmail.com'  # All apps on appspot.com use this for mail.

# Query parameters which are automatically preserved on page transition
# if you use utils.BaseHandler.get_url() or
# env.hidden_input_tags_for_preserved_query_params.
PRESERVED_QUERY_PARAM_NAMES = ['ui', 'charsets', 'referrer']

@register.filter
def get_value(dictionary, key):
    """Django Template filter to get dictionary value based on the given key"""
    return dictionary.get(key)

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
    params = dict(urlparse.parse_qsl(params))
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


def validate_checkbox_as_bool(val):
    if val.lower() in ['on', 'yes', 'true']:
        return True
    return False


def validate_role(string):
    return (strip(string).lower() == 'provide') and 'provide' or 'seek'


def validate_int(string):
    return string and int(strip(string))


def validate_float(string):
    return string and float(strip(string))


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


AGE_RE = re.compile(r'^(\d+)(-(\d+))?$')
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


DATETIME_RE = re.compile(r'^(2\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z$')


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


def validate_django_image(uploaded_file):
    """Tries to convert an image from Django to an Images API object.

    This is essentially a variant of validate_image, above, but for images that
    are uploaded to a Django handler (which gives us something different than
    webapp2 did). If the image is validated, it returns an Image object (from
    the App Engine Images API). Otherwise, it returns False.
    """
    try:
        image = None
        if uploaded_file:
            image = images.Image(uploaded_file.read())
            image.width
        return image
    except:
        return False


EMAIL_VALIDATOR = EmailValidator()


def validate_email(email):
    """Validates an email address, returning True on correct,
    False on incorrect, None on empty string."""
    # Note that google.appengine.api.mail.is_email_valid() is unhelpful;
    # it checks only for the empty string
    if not email:
        return None
    try:
        EMAIL_VALIDATOR(email)
        return True
    except ValidationError:
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


# ==== Fuzzification functions =================================================

# The range should be no more specific than a five year period.
MIN_AGE_RANGE = 5

def fuzzify_age(value):
    """Fuzzifies the age value for privacy.

    Args:
        value: a PFIF-compliant age value (a number or range, e.g., 45-49).

    Returns:
        A range of at least five years that includes the given value, or None if
        the input value is None or invalid.
    """
    if not value:
        return None
    parse = AGE_RE.match(value)
    if not parse:
        return None
    range_start = int(parse.group(1))
    range_end = int(parse.group(3)) if parse.group(3) else None
    if not range_end:
        # If no range was given, use a round five years around the given age.
        range_start -= range_start % MIN_AGE_RANGE
        return '%d-%d' % (range_start, range_start + MIN_AGE_RANGE)
    if (range_end - range_start) >= MIN_AGE_RANGE:
        # If the range we were given is already acceptably wide, leave it as-is.
        return value
    # If we were given too specific a range, pad it out to a round five year
    # range.
    range_start -= range_start % MIN_AGE_RANGE
    range_end += MIN_AGE_RANGE - ((range_end) % MIN_AGE_RANGE)
    return '%d-%d' % (range_start, range_end)


# ==== Other utilities =========================================================


def get_app_name():
    """Canonical name of the app, without HR s~ nonsense.  This only works in
    the context of the appserver (eg remote_api can't use it)."""
    from google.appengine.api import app_identity
    return app_identity.get_application_id()


def sanitize_urls(record):
    """Clean up URLs to protect against XSS.

    We check URLs submitted through Person Finder, but bad data might come in
    through the API.
    """
    url_validator = URLValidator(schemes=['http', 'https'])
    # Single-line URLs.
    for field in ['photo_url', 'source_url']:
        url = getattr(record, field, None)
        if not url:
            continue
        try:
            url_validator(url)
        except ValidationError:
            setattr(record, field, None)
    # Multi-line URLs.
    for field in ['profile_urls']:
        urls = (getattr(record, field, None) or '').splitlines()
        sanitized_urls = []
        for url in urls:
            if url:
                try:
                    url_validator(url)
                    sanitized_urls.append(url)
                except ValidationError:
                    logging.warning(
                        'Unsanitary URL in database on %s' % record.record_id)
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


# List of sensitive field names in person and note records.
SENSITIVE_FIELDS = [
  'date_of_birth',
  'author_email',
  'author_phone',
  'email_of_found_person',
  'phone_of_found_person',
]


def optionally_filter_sensitive_fields(records, auth=None):
    """Removes sensitive fields from a list of dictionaries, unless the client
    has full read authorization.

    Args:
        records (list of dict): A list of dictionaries which represent either of:
            - a person record
            - a note record
            - a joined record of a person and a note
    """
    if not (auth and auth.full_read_permission):
        filter_sensitive_fields(records)


def filter_sensitive_fields(records):
    """Removes sensitive fields from a list of dictionaries.

    Args:
        records (list of dict): A list of dictionaries which represent either of:
            - a person record
            - a note record
            - a joined record of a person and a note
    """
    for record in records:
        for prefix in ['', 'person_', 'note_']:
            for field in SENSITIVE_FIELDS:
                prefixed_field = prefix + field
                if prefixed_field in record:
                    record[prefixed_field] = ''


def join_person_and_note_record(person_record, note_record):
    """Join a person record and a note record into a single dictionary.

    The field names are prefixed with 'person_' or 'note_' to avoid name
    collision. note_record can be None. In that case, person record field
    names are still prefixed.

    Args:
        person_record (dict): A dictionary representation of a person record.
            Cannot be None.
        note_record (dict): A dictionary representation of a note record for
            the person. Can be None.
    """
    joined_record = {}
    for name, value in person_record.iteritems():
        new_name = get_field_name_for_joined_record(name, 'person')
        joined_record[new_name] = value
    if note_record:
        assert (note_record['person_record_id'] ==
                person_record['person_record_id'])
        for name, value in note_record.iteritems():
            new_name = get_field_name_for_joined_record(name, 'note')
            joined_record[new_name] = value
    return joined_record


def get_field_name_for_joined_record(original_field_name, record_type):
    """Converts a field name in a person/note record into a field name used in
    a joined record of a person and a note.

    See also join_person_and_note_record().

    Args:
        original_field_name (str): A field name in a person/note record.
        record_type (str): 'person' or 'note'.
    """
    if original_field_name in ('person_record_id', 'note_record_id'):
        return original_field_name
    else:
        return '%s_%s' % (record_type, original_field_name)


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


def send_confirmation_email_to_record_author(
    handler, person, action, confirm_url, record_id):
    """Send the author an email to confirm enabling/disabling notes
    of a record."""
    if not person.author_email:
        return handler.error(
            400, _('No author email for record %(id)s.') % {'id' : record_id})

    # i18n: Subject line of an e-mail message confirming the author
    # wants to disable notes for this record
    if action == 'enable':
        subject = _('[Person Finder] Enable notes on "%(full_name)s"?'
                ) % {'full_name': person.primary_full_name}
    elif action == 'disable':
        subject = _('[Person Finder] Disable notes on "%(full_name)s"?'
                ) % {'full_name': person.primary_full_name}
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
            full_name=person.primary_full_name,
            site_url=handler.get_url('/'),
            confirm_url=confirm_url
        )
    )


def get_repo_url(request, repo, scheme=None):
    """Constructs the absolute root URL for a given repository."""
    req_scheme, req_netloc, req_path, _, _ = urlparse.urlsplit(request.url)
    prefix = req_path.startswith('/personfinder') and '/personfinder' or ''
    if is_dev_app_server():
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


def add_profile_icon_url(website, url_builder):
    website = copy.deepcopy(website)  # avoid modifying the original
    website['icon_url'] = url_builder('/static/%s' % website['icon_filename'])
    return website


def strip_url_scheme(url):
    if not url:
        return url
    _, netloc, path, query, segment = urlparse.urlsplit(url)
    return urlparse.urlunsplit(('', netloc, path, query, segment))


def is_dev_app_server():
    return os.environ['APPLICATION_ID'].startswith('dev~')

# ==== Struct ==================================================================

class Struct:
    """A simple bag of attributes."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def get(self, name, default=None):
        return self.__dict__.get(name, default)


# ==== Key management ======================================================

def generate_random_key(length):
    """Generates a random key with given length."""
    source = ('abcdefghijklmnopqrstuvwxyz'
              'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
              '1234567890'
              '-_')
    rng = random.SystemRandom()
    return ''.join(rng.choice(source) for i in range(length))


# ==== Decorators  ============================================================

def require_api_key_management_permission(handler_method):
    """
    This is a decorator for API Key management feature. The limitation
    is that the decorator can not preserve payloads within a POST/PUT
    request.

    Usage:
    class SomeHandler(utils.BaseHandler):
        @utils.require_api_key_management_permission
        def get(self):
            # ....
            # ....
    """
    def inner(*args, **kwargs):
        handler = args[0]
        user = users.get_current_user()
        if (users.is_current_user_admin() or
            (user and handler.config.key_management_operators and
             user.email() in handler.config.key_management_operators)):
            return handler_method(*args, **kwargs)
        else:
            return handler.redirect(
                users.create_login_url(handler.request.url))
    return inner


# ==== Base Handler ============================================================

class BaseHandler(webapp.RequestHandler):
    # Handlers that don't need a repository name can set this to False.
    repo_required = True

    # Handlers that require HTTPS can set this to True.
    https_required = True

    # Set this to True to enable a handler even for deactivated repositories.
    ignore_deactivation = False

    # Handlers that require an admin permission must set this to True.
    admin_required = False

    # List all accepted query parameters here with their associated validators.
    auto_params = {
        'action': strip,
        'add_note': validate_yes,
        'age': validate_age,
        'alternate_family_names': strip,
        'alternate_given_names': strip,
        'author_email': strip,
        'author_made_contact': validate_yes,
        'author_name': strip,
        'author_phone': strip,
        'your_own_email': strip,
        'your_own_phone': strip,
        'believed_dead_permission': validate_checkbox_as_bool,
        'cache_seconds': validate_cache_seconds,
        'clone': validate_yes,
        'confirm': validate_yes,
        'contact_email': strip,
        'contact_name': strip,
        'content_id': strip,
        'context': strip,
        'cursor': strip,
        'date_of_birth': validate_approximate_date,
        'description': strip,
        'domain_write_permission': strip,
        'dupe_notes': validate_yes,
        'email_of_found_person': strip,
        'error': strip,
        'expiry_option': validate_expiry,
        'family_name': strip,
        'full_read_permission': validate_checkbox_as_bool,
        'given_name': strip,
        'home_city': strip,
        'home_country': strip,
        'home_neighborhood': strip,
        'home_postal_code': strip,
        'home_state': strip,
        'id': strip,
        'id1': strip,
        'id2': strip,
        'id3': strip,
        'is_valid': validate_checkbox_as_bool,
        'key': strip,
        'lang': validate_lang,
        'last_known_location': strip,
        'mark_notes_reviewed': validate_checkbox_as_bool,
        'max_results': validate_int,
        'min_entry_date': validate_datetime,
        'new_repo': validate_repo,
        'note_photo': validate_image,
        'note_photo_url': strip,
        'omit_notes': validate_yes,
        'operation': strip,
        'organization_name': strip,
        'person_record_id': strip,
        'phone_of_found_person': strip,
        'photo': validate_image,
        'photo_url': strip,
        'profile_url1': strip,
        'profile_url2': strip,
        'profile_url3': strip,
        'query': strip,
        'query_name': strip,
        'query_location': strip,
        'query_type': strip,
        'read_permission': validate_checkbox_as_bool,
        'referrer': strip,
        'resource_bundle': validate_resource_name,
        'resource_bundle_default': validate_resource_name,
        'resource_bundle_original': validate_resource_name,
        'resource_lang': validate_lang,
        'resource_name': validate_resource_name,
        'role': validate_role,
        'search_engine_id': validate_int,
        'search_permission': validate_checkbox_as_bool,
        'sex': validate_sex,
        'signature': strip,
        'skip': validate_int,
        'small': validate_yes,
        'source': strip,
        'source_date': strip,
        'source_name': strip,
        'source_url': strip,
        'stats_permission': validate_checkbox_as_bool,
        'status': validate_status,
        'style': strip,
        'subscribe': validate_checkbox,
        'subscribe_own_info': validate_checkbox,
        'subscribe_email': strip,
        'subscribe_permission': validate_checkbox_as_bool,
        'suppress_redirect': validate_yes,
        'target': strip,
        'text': strip,
        'thumb': validate_checkbox_as_bool,
        'timestamp': validate_timestamp,
        'ui': strip_and_lower,
        'utcnow': validate_timestamp,
        'version': validate_version,
        'own_info': validate_yes,
        'xsrf_token': strip,
    }

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
            vars.update(get_vars())
            for key in ('env', 'config', 'params'):
                if key in vars:
                    raise Exception(
                        'Cannot use "%s" as a key in vars. It is reserved.'
                        % key)
            vars['env'] = self.env  # pass along application-wide context
            vars['config'] = self.config  # pass along the configuration
            vars['params'] = self.params  # pass along the query parameters
            return vars
        return resources.get_rendered(
            name, lang, extra_key, get_all_vars, cache_seconds)

    def error(self, code, message='', message_html=''):
        self.info(code, message, message_html, style='error')

    def info(self, code, message='', message_html='', style='info'):
        """Renders a simple page with a message.

        Args:
          code: HTTP status code.
          message: A message in plain text.
          message_html: A message in HTML.
          style: 'info', 'error' or 'plain'. 'info' and 'error' differs in
              appearance. 'plain' just renders the message without extra
              HTML tags. Good for API response.
        """
        is_error = 400 <= code < 600
        if is_error:
            webapp.RequestHandler.error(self, code)
        else:
            self.response.set_status(code)
        if not message and not message_html:
            message = '%d: %s' % (code, httplib.responses.get(code))
        if style == 'plain':
            self.__render_plain_message(message, message_html)
        else:
            try:
                self.render('message.html', cls=style,
                            message=message, message_html=message_html)
            except:
                self.__render_plain_message(message, message_html)
        self.terminate_response()

    def __render_plain_message(self, message, message_html):
        self.response.out.write(
            django.utils.html.escape(message) +
            ('<p>' if message and message_html else '') +
            message_html)

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

    def transitionary_get_url(self, path, repo=None, params=None):
        """Gets a URL to the given path, with the given params.

        We want to share some code between Django and webapp2 handlers (also,
        I'd like to get away from embedding so much code in the handlers), and a
        significant obstacle to that is that you can only create URLs from
        handlers. The solution seems to be passing a URL-building function into
        functions that need to build URLs.

        The Django app has a somewhat different URL builder for various reasons,
        and this function matches its signature so that functions don't have to
        know what web framework their URL-building function came from.
        """
        if params:
            param_dict = {k: v for k, v in params}
        if not params:
            param_dict = {}
        return get_url(self.request, repo, path, **param_dict)

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

        return recaptcha.client.captcha.get_display_html(
            site_key=config.get('captcha_site_key'),
            use_ssl=use_ssl, error=error_code, lang=lang
        )

    def get_captcha_response(self):
        """Returns an object containing the CAPTCHA response information for the
        given request's CAPTCHA field information."""
        # Allows faking the CAPTCHA response by an HTTP request parameter, but
        # only locally, for testing purpose.
        faked_captcha_response = self.request.get('faked_captcha_response')
        if faked_captcha_response and self.request.remote_addr == '127.0.0.1':
            return recaptcha.client.captcha.RecaptchaResponse(
                is_valid=faked_captcha_response == 'success')

        captcha_response = self.request.get('g-recaptcha-response')
        return recaptcha.client.captcha.submit(captcha_response)

    def handle_exception(self, exception, debug_mode):
        logging.error(traceback.format_exc())
        self.error(500, _(
            'There was an error processing your request.  Sorry for the '
            'inconvenience.  Our administrators will investigate the source '
            'of the problem, but please check that the format of your '
            'request is correct.'))

    def __get_env_language_for_babel(self):
        language_code = self.env.lang
        try:
            return babel.Locale.parse(language_code, sep='-')
        except babel.UnknownLocaleError as e:
            # fallback language
            return babel.Locale('en')

    def to_local_time(self, date):
        """Converts a datetime object to the local time configured for the
        current repository.  For convenience, returns None if date is None."""
        # TODO(kpy): This only works for repositories that have a single fixed
        # time zone offset and never use Daylight Saving Time.
        if date:
            if self.config.time_zone_offset:
                return date + timedelta(0, 3600*self.config.time_zone_offset)
            return date

    def format_datetime_localized(self, dt):
        """Formats a datetime object to a localized human-readable string based
        on the current locale."""
        return format_datetime(dt, locale=self.__get_env_language_for_babel());

    def format_date_localized(self, dt):
        """Formats a datetime object to a localized human-readable string based
        on the current locale containing only the date."""
        return format_date(dt, locale=self.__get_env_language_for_babel());

    def format_time_localized(self, dt):
        """Formats a datetime object to a localized human-readable string based
        on the current locale containing only the time."""
        return format_time(dt, locale=self.__get_env_language_for_babel());

    def to_formatted_local_datetime(self, dt):
        """Converts a datetime object to the local datetime configured for the
        current repository and formats to a localized human-readable string
        based on the current locale."""
        dt = self.to_local_time(dt)
        return self.format_datetime_localized(dt)

    def to_formatted_local_date(self, dt):
        """Converts a datetime object to the local date configured for the
        current repository and formats to a localized human-readable string
        based on the current locale."""
        dt = self.to_local_time(dt)
        return self.format_date_localized(dt)

    def to_formatted_local_time(self, dt):
        """Converts a datetime object to the local time configured for the
        current repository and formats to a localized human-readable string
        based on the current locale."""
        dt = self.to_local_time(dt)
        return self.format_time_localized(dt)

    def maybe_redirect_for_repo_alias(self, request):
        """If the specified repository name is an alias, redirects to the URL
        with the canonical repository name and returns True. Otherwise returns
        False.
        """
        # Config repo_alias is a dictionary from a repository name alias to
        # its canonical.
        # e.g., {'yol': '2013-yolanda', 'jam': '2014-jammu-kashmir-floods'}
        #
        # A repository name alias can be used instead of the canonical
        # repository name in URLs. This is especially useful combined with
        # the short URL. e.g., You can access
        # https://www.google.org/personfinder/2014-jammu-kashmir-floods
        # by https://g.co/pf/jam .
        if not self.repo:
            return False
        repo_aliases = config.get('repo_aliases', default={})
        if self.repo in repo_aliases:
            canonical_repo = repo_aliases[self.repo]
            params = {}
            for name in request.arguments():
                params[name] = request.get(name)
            # Redirects to the same URL including the query parameters, except
            # for the repository name.
            self.redirect('/' + self.env.action, repo=canonical_repo, **params)
            self.terminate_response()
            return True
        else:
            return False

    def should_show_inline_photo(self, photo_url):
        """Returns True if we should show the photo in our site directly with
        <img> tag. Returns True only if the photo is served by our domain, to
        avoid loading resources in other domains in Person Finder.
        """
        if not photo_url:
            return False
        else:
            _, our_netloc, _, _, _ = urlparse.urlsplit(self.request.url)
            _, photo_netloc, _, _, _ = urlparse.urlsplit(photo_url)
            return photo_netloc == our_netloc

    URL_PARSE_QUERY_INDEX = 4

    def get_thumbnail_url(self, photo_url):
        """Get a thumbnail URL for an uploaded photo's URL.

        Args:
            photo_url: a photo URL for an uploaded photo
        """
        if not photo_url:
            return None
        parsed_url = list(urlparse.urlparse(photo_url))
        params_dict = dict(urlparse.parse_qsl(
            parsed_url[BaseHandler.URL_PARSE_QUERY_INDEX]))
        params_dict['thumb'] = 'true'
        parsed_url[BaseHandler.URL_PARSE_QUERY_INDEX] = urllib.urlencode(
            params_dict)
        return urlparse.urlunparse(parsed_url)

    def set_auth(self):
        self.auth = None
        if self.params.key:
            if self.repo:
                # check for domain specific one.
                self.auth = model.Authorization.get(self.repo, self.params.key)
            if not self.auth:
                # perhaps this is a global key ('*' for consistency with config).
                self.auth = model.Authorization.get('*', self.params.key)
        if self.auth and not self.auth.is_valid:
            self.auth = None

    def __return_unimplemented_method_error(self):
        return self.error(
            405,
            'HTTP method %s is not allowed for this URL.'
                % self.request.method)

    def __init__(self, request, response, env):
        webapp.RequestHandler.__init__(self, request, response)
        self.params = Struct()
        self.env = env
        self.repo = env.repo
        self.config = env.config
        self.charset = env.charset

        # Set default Content-Type header.
        self.response.headers['Content-Type'] = (
            'text/html; charset=%s' % self.charset)
        if self.admin_required:
            self.response.headers['X-Frame-Options'] = 'SAMEORIGIN'

        # Validate query parameters.
        for name, validator in self.auto_params.items():
            try:
                value = self.request.get(name, '')
                setattr(self.params, name, validator(value))
            except Exception, e:
                setattr(self.params, name, validator(None))
                return self.error(400, 'Invalid parameter %s: %s' % (name, e))

        # Ensure referrer is in whitelist, if it exists
        if self.params.referrer and (not self.params.referrer in
                                     self.config.referrer_whitelist):
            setattr(self.params, 'referrer', '')

        # Check for SSL (unless running local dev app server).
        if self.https_required and not is_dev_app_server():
            if self.env.scheme != 'https':
                url_parts = list(urlparse.urlparse(self.request.url))
                url_parts[0] = 'https'  # The 0th part is the scheme.
                webapp.RequestHandler.redirect(
                    self, urlparse.urlunparse(url_parts))
                self.terminate_response()
                return

        # Handles repository alias.
        if self.maybe_redirect_for_repo_alias(request):
            return

        # Shows a custom error page here when the user is not an admin
        # instead of "login: admin" in app.yaml
        # If we use it, user can't sign out
        # because the error page of "login: admin" doesn't have sign-out link.
        if self.admin_required:
            self.env.user = users.get_current_user()
            if not self.env.user:
                login_url = users.create_login_url(self.request.url)
                webapp.RequestHandler.redirect(self, login_url)
                self.terminate_response()
                return
            if not users.is_current_user_admin():
                logout_url = users.create_logout_url(self.request.url)
                self.render('not_admin_error.html', logout_url=logout_url,
                            user=self.env.user)
                self.terminate_response()
                return
            self.env.logout_url = users.create_logout_url(self.request.url)
            # This is different from env.repo_options because this contains all
            # repositories including deactivated ones.
            self.env.all_repo_options = [
                Struct(
                    repo=repo,
                    url=get_repo_url(self.request, repo) + '/admin')
                for repo in sorted(model.Repo.list())]

        # Handlers that don't need a repository configuration can skip it.
        if not self.repo:
            if self.repo_required:
                return self.error(400, 'No repository specified.')
            return
        # Everything after this requires a repo.

        # Reject requests for repositories that don't exist.
        if not model.Repo.get_by_key_name(self.repo):
            html = 'No such repository. '
            if self.env.repo_options:
                html += 'Select:<p>' + self.render_to_string('repo-menu.html')
            return self.error(404, message_html=html)

        # If this repository has been deactivated, terminate with a message.
        # The ignore_deactivation flag is for admin pages that bypass this.
        if (self.env.repo_entity.is_deactivated() and
            not self.ignore_deactivation):
            self.env.language_menu = []
            self.env.robots_ok = True
            self.render('message.html', cls='deactivation',
                        message_html=self.config.deactivation_message_html)
            self.terminate_response()

    def get(self, *args):
        """Default handler implementation which returns HTTP status 405."""
        return self.__return_unimplemented_method_error()

    def post(self, *args):
        """Default handler implementation which returns HTTP status 405."""
        return self.__return_unimplemented_method_error()

    def put(self, *args):
        """Default handler implementation which returns HTTP status 405."""
        return self.__return_unimplemented_method_error()

    def head(self, *args):
        """Default handler implementation which returns HTTP status 405."""
        return self.__return_unimplemented_method_error()

    def options(self, *args):
        """Default handler implementation which returns HTTP status 405."""
        return self.__return_unimplemented_method_error()

    def delete(self, *args):
        """Default handler implementation which returns HTTP status 405."""
        return self.__return_unimplemented_method_error()

    def trace(self, *args):
        """Default handler implementation which returns HTTP status 405."""
        return self.__return_unimplemented_method_error()


# ==== XSRF protection =========================================================

class XsrfTool(object):

    # XSRF tokens expire after 4 hours.
    TOKEN_EXPIRATION_TIME = 60 * 60 * 4

    def __init__(self):
        configured_key = config.get('xsrf_token_key')
        if configured_key:
            # config.get returns unicode, but hmac is going to want a str
            self._key = configured_key.encode('utf-8')
        else:
            configured_key = generate_random_key(20)
            config.set(xsrf_token_key=configured_key)
            self._key = configured_key

    def generate_token(self, user_id, action_id):
        action_time = get_utcnow_timestamp()
        return '%s/%f' % (
            self._generate_hmac_digest(user_id, action_id, action_time),
            action_time)

    def verify_token(self, token, user_id, action_id):
        token_spl = token.split('/')
        if len(token_spl) != 2:
            return False
        [hmac_digest, action_time_str] = token_spl
        action_time = float(action_time_str)
        if (action_time + XsrfTool.TOKEN_EXPIRATION_TIME <
            get_utcnow_timestamp()):
            return False
        expected_hmac_digest = self._generate_hmac_digest(
            user_id, action_id, action_time)
        return hmac.compare_digest(
            hmac_digest.encode('utf-8'), expected_hmac_digest)

    def _generate_hmac_digest(self, user_id, action_id, action_time):
        hmac_obj = hmac.new(
            self._key, '%s/%s/%f' % (user_id, action_id, action_time))
        return hmac_obj.hexdigest()
