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

"""The main request handler.  All dynamic requests except for remote_api are
handled by this handler, which dispatches to all other dynamic handlers."""

import django_setup  # always keep this first

import mimetypes
import re
import urlparse

from google.appengine.api import memcache
from google.appengine.ext import webapp

import config
import const
import legacy_redirect
import pfif
import resources
import utils


# When no action or repo is specified, redirect to this action.
HOME_ACTION = 'howitworks'

# Map of URL actions to Python module and class names.
# TODO(kpy): Remove the need for this configuration information, either by
# regularizing the module and class names or adding a URL attribute to handlers.
HANDLER_CLASSES = dict((x, x.replace('/', '_') + '.Handler') for x in [
  'start',
  'query',
  'results',
  'create',
  'view',
  'multiview',
  'reveal',
  'photo',
  'embed',
  'extend',
  'gadget',
  'delete',
  'flag_note',
  'restore',
  'subscribe',
  'unsubscribe',
  'disable_notes',
  'confirm_disable_notes',
  'enable_notes',
  'confirm_enable_notes',
  'post_flagged_note',
  'confirm_post_flagged_note',
  'admin',
  'admin/dashboard',
  'admin/resources',
  'admin/review',
])

# Exceptional cases where the module name doesn't match the URL.
HANDLER_CLASSES[''] = 'start.Handler'
HANDLER_CLASSES['howitworks'] = 'googleorg.Handler'
HANDLER_CLASSES['faq'] = 'googleorg.Handler'
HANDLER_CLASSES['responders'] = 'googleorg.Handler'
HANDLER_CLASSES['api/read'] = 'api.Read'
HANDLER_CLASSES['api/write'] = 'api.Write'
HANDLER_CLASSES['api/search'] = 'api.Search'
HANDLER_CLASSES['api/subscribe'] = 'api.Subscribe'
HANDLER_CLASSES['api/unsubscribe'] = 'api.Unsubscribe'
HANDLER_CLASSES['feeds/note'] = 'feeds.Note'
HANDLER_CLASSES['feeds/person'] = 'feeds.Person'
HANDLER_CLASSES['sitemap'] = 'sitemap.SiteMap'
HANDLER_CLASSES['sitemap/ping'] = 'sitemap.SiteMapPing'
HANDLER_CLASSES['tasks/count/note'] = 'tasks.CountNote'
HANDLER_CLASSES['tasks/count/person'] = 'tasks.CountPerson'
HANDLER_CLASSES['tasks/count/reindex'] = 'tasks.Reindex'
HANDLER_CLASSES['tasks/count/update_status'] = 'tasks.UpdateStatus'
HANDLER_CLASSES['tasks/delete_expired'] = 'tasks.DeleteExpired'
HANDLER_CLASSES['tasks/delete_old'] = 'tasks.DeleteOld'

def get_repo_and_action(request):
    """Determines the repo and action for a request.  The action is the part
    of the URL path after the repo, with no leading or trailing slashes."""
    scheme, netloc, path, _, _ = urlparse.urlsplit(request.url)
    parts = path.lstrip('/').split('/')

    # TODO(kpy): Remove support for legacy URLs in mid-January 2012.
    import legacy_redirect
    if legacy_redirect.get_subdomain(request):
        repo = legacy_redirect.get_subdomain(request)
        action = '/'.join(parts)
        return repo, action

    # Depending on whether we're serving from appspot directly or
    # google.org/personfinder we could have /global or /personfinder/global
    # as the 'global' prefix.
    if parts[0] == 'personfinder':
        parts.pop(0)
    repo = parts and parts.pop(0) or None
    action = '/'.join(parts)
    if repo == 'global':
        repo = None
    return repo, action

def select_charset(request):
    """Given a request, chooses a charset for encoding the response."""
    # We assume that any client that doesn't support UTF-8 will specify a
    # preferred encoding in the Accept-Charset header, and will use this
    # encoding for content, query parameters, and form data.  We make this
    # assumption across all repositories.
    # (Some Japanese mobile phones support only Shift-JIS and expect
    # content, parameters, and form data all to be encoded in Shift-JIS.)

    # Get a list of the charsets that the client supports.
    if request.get('charsets'): # allow override for testing
        charsets = request.get('charsets').split(',')
    else:
        charsets = request.accept_charset.best_matches()

    # Always prefer UTF-8 if the client supports it.
    for charset in charsets:
        if charset.lower().replace('_', '-') in ['utf8', 'utf-8']:
            return charset

    # Otherwise, look for a requested charset that Python supports.
    for charset in charsets:
        try:
            'xyz'.encode(charset, 'replace')  # test if charset is known
            return charset
        except:
            continue

    # If Python doesn't know any of the requested charsets, use UTF-8.
    return 'utf-8'

def select_lang(request, config=None):
    """Selects the best language to use for a given request.  The 'lang' query
    parameter has priority, then the django_language cookie, then the first
    language in the language menu, then the default setting."""
    default_lang = (config and
                    config.language_menu_options and
                    config.language_menu_options[0])
    lang = (request.get('lang') or
            request.cookies.get('django_language', None) or
            default_lang or
            django_setup.LANGUAGE_CODE)
    lang = re.sub('[^A-Za-z0-9-]', '', lang)
    return const.LANGUAGE_SYNONYMS.get(lang, lang)

def get_repo_options(request, lang):
    """Returns a list of the names and titles of the active repositories."""
    options = []
    for repo in config.get('active_repos') or []:
        titles = config.get_for_repo(repo, 'repo_titles', {})
        default_title = (titles.values() or ['?'])[0]
        title = titles.get(lang, titles.get('en', default_title))
        url = utils.get_repo_url(request, repo)
        options.append(utils.Struct(repo=repo, title=title, url=url))
    return options

def get_language_options(request, config=None):
    """Returns a list of information needed to generate the language menu."""
    return [{'lang': lang,
             'endonym': const.LANGUAGE_ENDONYMS.get(lang, '?'),
             'url': utils.set_url_param(request.url, 'lang', lang)}
            for lang in (config and config.language_menu_options or ['en'])]

def get_secret(name):
    """Gets a secret from the datastore by name, or returns None if missing."""
    import model
    secret = model.Secret.get_by_key_name(name)
    if secret:
        return secret.secret

def get_localized_message(localized_messages, lang, default):
    """Gets the localized message for lang from a dictionary that maps language
    codes to localized messages.  Falls back to English if language 'lang' is
    not available, or to a default message if English is not available."""
    if not isinstance(localized_messages, dict):
        return default
    return localized_messages.get(lang, localized_messages.get('en', default))

def setup_env(request):
    """Constructs the 'env' object, which contains various template variables
    that are commonly used by most handlers."""
    env = utils.Struct()
    env.repo, env.action = get_repo_and_action(request)
    env.config = env.repo and config.Configuration(env.repo)
    env.test_mode = (request.remote_addr == '127.0.0.1' and
                     request.get('test_mode'))

    # TODO(kpy): Make these global config settings and get rid of get_secret().
    env.analytics_id = get_secret('analytics_id')
    env.maps_api_key = get_secret('maps_api_key')

    # Internationalization-related stuff.
    env.charset = select_charset(request)
    env.lang = select_lang(request, env.config)
    env.rtl = env.lang in django_setup.LANGUAGES_BIDI
    env.virtual_keyboard_layout = const.VIRTUAL_KEYBOARD_LAYOUTS.get(env.lang)
    env.back_chevron = env.rtl and u'\xbb' or u'\xab'

    # Determine the resource bundle to use.
    env.default_resource_bundle = config.get('default_resource_bundle', '1')
    env.resource_bundle = (request.cookies.get('resource_bundle', '') or
                           env.default_resource_bundle)

    # Information about the request.
    env.url = utils.set_url_param(request.url, 'lang', env.lang)
    env.scheme, env.netloc, env.path, _, _ = urlparse.urlsplit(request.url)
    env.domain = env.netloc.split(':')[0]
    env.global_url = utils.get_repo_url(request, 'global')

    # Commonly used information that's rendered or localized for templates.
    env.language_options = get_language_options(request, env.config)
    env.repo_options = get_repo_options(request, env.lang)
    env.expiry_options = [
        utils.Struct(value=value, text=const.PERSON_EXPIRY_TEXT[value])
        for value in sorted(const.PERSON_EXPIRY_TEXT.keys(), key=int)
    ]
    env.status_options = [
        utils.Struct(value=value, text=const.NOTE_STATUS_TEXT[value])
        for value in pfif.NOTE_STATUS_VALUES
        if (value != 'believed_dead' or
            not env.config or env.config.allow_believed_dead_via_ui)
    ]

    # Fields related to "small mode" (for embedding in an <iframe>).
    env.small = request.get('small', '').lower() == 'yes'
    # Optional "target" attribute for links to non-small pages.
    env.target_attr = env.small and ' target="_blank" ' or ''

    # Repo-specific information.
    if env.repo:
        # repo_url is the root URL for the repository.
        env.repo_url = utils.get_repo_url(request, env.repo)
        # start_url is like repo_url but preserves 'small' and 'style' params.
        env.start_url = utils.get_url(request, env.repo, '')
        env.repo_path = urlparse.urlsplit(env.repo_url)[2]
        env.repo_title = get_localized_message(
            env.config.repo_titles, env.lang, '?')
        env.start_page_custom_html = get_localized_message(
            env.config.start_page_custom_htmls, env.lang, '')
        env.results_page_custom_html = get_localized_message(
            env.config.results_page_custom_htmls, env.lang, '')
        env.view_page_custom_html = get_localized_message(
            env.config.view_page_custom_htmls, env.lang, '')
        env.seek_query_form_custom_html = get_localized_message(
            env.config.seek_query_form_custom_htmls, env.lang, '')

        # Preformat the name from the 'first_name' and 'last_name' parameters.
        first = request.get('first_name', '').strip()
        last = request.get('last_name', '').strip()
        env.params_full_name = utils.get_full_name(first, last, env.config)

    return env

def flush_caches(*keywords):
    """Flushes the specified set of caches.  Pass '*' to flush everything."""
    if '*' in keywords or 'resource' in keywords:
       resources.clear_caches()
    if '*' in keywords or 'memcache' in keywords:
       memcache.flush_all()
    if '*' in keywords or 'config' in keywords:
       config.cache.flush()
    for keyword in keywords:
        if keyword.startswith('config/'):
            config.cache.delete(keyword[7:])


class Main(webapp.RequestHandler):
    """The main request handler.  All dynamic requests except for remote_api are
    handled by this handler, which dispatches to all other dynamic handlers."""

    def initialize(self, request, response):
        webapp.RequestHandler.initialize(self, request, response)

        # If requested, set the clock before doing anything clock-related.
        # Only works on localhost for testing.  Specify ?utcnow=1293840000 to
        # set the clock to 2011-01-01, or ?utcnow=real to revert to real time.
        utcnow = request.get('utcnow')
        if request.remote_addr == '127.0.0.1' and utcnow:
            if utcnow == 'real':
                utils.set_utcnow_for_test(None)
            else:
                utils.set_utcnow_for_test(float(utcnow))

        # If requested, flush caches before we touch anything that uses them.
        flush_caches(*request.get('flush', '').split(','))

        # check for legacy redirect:
        # TODO(lschumacher|kpy): remove support for legacy URLS Q1 2012.
        if legacy_redirect.do_redirect(self):
            # stub out get/head to prevent failures.
            self.get = self.head = lambda *args: None
            return legacy_redirect.redirect(self)

        # Gather commonly used information into self.env.
        self.env = setup_env(request)
        request.charset = self.env.charset  # used for parsing query params

        # Activate the selected language.
        response.headers['Content-Language'] = self.env.lang
        response.headers['Set-Cookie'] = \
            'django_language=%s; path=/' % self.env.lang
        django_setup.activate(self.env.lang)

        # Activate the appropriate resource bundle.
        resources.set_active_bundle_name(self.env.resource_bundle)

    def serve(self):
        request, response, env = self.request, self.response, self.env
        if not env.action and not env.repo:
            # Redirect to the default home page.
            self.redirect(env.global_url + '/' + HOME_ACTION)
        elif env.action in HANDLER_CLASSES:
            # Dispatch to the handler for the specified action.
            module_name, class_name = HANDLER_CLASSES[env.action].split('.')
            handler = getattr(__import__(module_name), class_name)()
            handler.initialize(request, response, env)
            getattr(handler, request.method.lower())()  # get() or post()
        elif env.action.endswith('.template'):
            # Don't serve template source code.
            return self.error(404)
        else:
            # Serve a static page or file.
            env.robots_ok = True
            get_vars = lambda: {'env': env, 'config': env.config}
            content = resources.get_rendered(
                env.action, env.lang, (env.repo, env.charset), get_vars)
            if content is None:
                return self.error(404)
            content_type, content_encoding = mimetypes.guess_type(env.action)
            response.headers['Content-Type'] = content_type or 'text/plain'
            response.out.write(content)

    def get(self):
        self.serve()

    def post(self):
        self.serve()

    def head(self):
        self.request.method = 'GET'
        self.serve()
        self.response.clear()

if __name__ == '__main__':
    webapp.util.run_wsgi_app(webapp.WSGIApplication([('.*', Main)]))
