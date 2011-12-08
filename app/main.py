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

from google.appengine.ext import webapp
import re
import urlparse

import config
import const
import i18n_setup
import logging
import pfif
import utils


# Map of URL actions to Python module and class names.
# TODO(kpy): Remove the need for this configuration information, either by
# regularizing the module and class names or adding a URL attribute to handlers.
HANDLER_CLASSES = dict((x, x.replace('/', '_') + '.Handler') for x in [
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
  'admin/review',
])

# Exceptional cases where the module name doesn't match the URL.
HANDLER_CLASSES[''] = 'start.Handler'
HANDLER_CLASSES['howitworks'] = 'googleorg.Handler'
HANDLER_CLASSES['faq'] = 'googleorg.Handler'
HANDLER_CLASSES['responders'] = 'googleorg.Handler'
HANDLER_CLASSES['admin/set_utcnow_for_test'] = 'set_utcnow.Handler'
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

def get_repo(request):
    """Determines the repo for a request."""
    scheme, netloc, path, _, _ = urlparse.urlsplit(request.url)
    parts = path.split('/')
    repo = parts[1]
    # depending on if we're serving from appspot driectly or
    # google.org/personfinder we could have /global or /personfinder/global
    # as the 'global' prefix.
    if repo == 'personfinder' and len(parts) > 2:
        repo = parts[2]
    if repo == 'global' or repo == 'personfinder':
        return None
    return repo

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
            i18n_setup.LANGUAGE_CODE)
    return re.sub('[^A-Za-z-]', '', lang)

def get_repo_options(lang):
    """Returns a list of the names and titles of the active repositories."""
    options = []
    for repo in config.get('active_repos') or []:
        titles = config.get_for_repo(repo, 'repo_titles', {})
        default_title = (titles.values() or ['?'])[0]
        title = titles.get(lang, titles.get('en', default_title))
        options.append(utils.Struct(repo=repo, title=title))
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
    codes to localized messages.  Falls back to English if the specified language
    is not available, or to a default message if English is not available."""
    if not isinstance(localized_messages, dict):
        return default
    return localized_messages.get(lang, localized_messages.get('en', default))

def setup_env(request):
    """Constructs the 'env' object, which contains various template variables
    that are commonly used by most handlers."""
    env = utils.Struct()
    env.repo = get_repo(request)
    env.config = env.repo and config.Configuration(env.repo)

    # TODO(kpy): Make these global config settings and get rid of get_secret().
    env.analytics_id = get_secret('analytics_id')
    env.maps_api_key = get_secret('maps_api_key')

    # Internationalization-related stuff.
    env.charset = select_charset(request)
    env.lang = select_lang(request, env.config)
    env.rtl = env.lang in i18n_setup.LANGUAGES_BIDI
    env.virtual_keyboard_layout = const.VIRTUAL_KEYBOARD_LAYOUTS.get(env.lang)
    env.back_chevron = env.rtl and u'\xbb' or u'\xab'

    # Information about the request.
    env.url = utils.set_url_param(request.url, 'lang', env.lang)
    env.scheme, env.netloc, env.path, _, _ = urlparse.urlsplit(request.url)
    env.domain = env.netloc.split(':')[0]

    # Commonly used information that's rendered or localized for templates.
    env.language_options = get_language_options(request, env.config)
    env.repo_options = get_repo_options(env.lang)
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

    # Repo-specific information.
    if env.repo:
        env.repo_url = utils.get_repo_url(request, env.repo)
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

        # URLs that are used in the base template.
        env.start_url = utils.get_url(request, env.repo, '/')
        env.embed_url = utils.get_url(request, env.repo, '/embed')

    return env


class Main(webapp.RequestHandler):
    """The main request handler.  All dynamic requests except for remote_api are
    handled by this handler, which dispatches to all other dynamic handlers."""

    def get(self, repo, action):
        action = action.lstrip('/')
        env = setup_env(self.request)
        self.request.charset = env.charset  # used for parsing query params

        # Activate the selected language.
        i18n_setup.activate(env.lang)
        self.response.headers['Content-Language'] = env.lang
        self.response.headers['Set-Cookie'] = 'django_language=' + env.lang

        # Dispatch to the handler for the specified action.
        if action in HANDLER_CLASSES:
            module_name, class_name = HANDLER_CLASSES[action].split('.')
            response = webapp.Response()

            # Instantiate the handler class and call the get() or post() method.
            handler = getattr(__import__(module_name), class_name)()
            handler.initialize(self.request, response, env)
            logging.info('%r %r %r' % (handler, self.request.method, action))
            getattr(handler, self.request.method.lower())()

            # Forward the results to the real handler.
            if response.has_error():  # pass along the error
                self.response.set_status(
                    response.status, response.status_message)
            self.response.headers['Content-Type'] = \
                response.headers['Content-Type'] + '; charset=' + env.charset
            self.response.out.write(response.out.getvalue())
        else:
            self.error(404)

    def post(self, repo, action):
        self.get(repo, action)

    def head(self, repo, action):
        self.get(repo, action)
        self.response.clear()

if __name__ == '__main__':
    webapp.util.run_wsgi_app(webapp.WSGIApplication([
        ('/personfinder/([a-z0-9-]+)(/?.*)', Main),
        ('/([a-z0-9-]+)(/?.*)', Main)
    ]))
