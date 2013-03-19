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
import django.utils.html
import legacy_redirect
import logging
import pfif
import resources
import utils
import user_agents


# When no action or repo is specified, redirect to this action.
HOME_ACTION = 'home.html'

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
HANDLER_CLASSES['api/import'] = 'api.Import'
HANDLER_CLASSES['api/read'] = 'api.Read'
HANDLER_CLASSES['api/write'] = 'api.Write'
HANDLER_CLASSES['api/search'] = 'api.Search'
HANDLER_CLASSES['api/subscribe'] = 'api.Subscribe'
HANDLER_CLASSES['api/unsubscribe'] = 'api.Unsubscribe'
HANDLER_CLASSES['feeds/repo'] = 'feeds.Repo'
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
HANDLER_CLASSES['tasks/clean_up_in_test_mode'] = 'tasks.CleanUpInTestMode'

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
    """Given a request, chooses a charset for encoding the response.

    If the selected charset is UTF-8, it always returns
    'utf-8' (const.CHARSET_UTF8), not 'utf8', 'UTF-8', etc.
    """
    # We assume that any client that doesn't support UTF-8 will specify a
    # preferred encoding in the Accept-Charset header, and will use this
    # encoding for content, query parameters, and form data.  We make this
    # assumption across all repositories.

    # Get a list of the charsets that the client supports.
    if request.get('charsets'):
        charsets = request.get('charsets').split(',')
    elif user_agents.prefer_sjis_charset(request):
        # Some Japanese feature phones don't (fully) support UTF-8.
        # They only support Shift_JIS. But they may not send Accept-Charset
        # header. Also, we haven't confirmed, but there may be phones whose
        # Accept-Charset header includes UTF-8 but its UTF-8 support is buggy.
        # So we always use Shift_JIS regardless of Accept-Charset header.
        charsets = ['Shift_JIS']
    else:
        charsets = request.accept_charset.best_matches()

    # Always prefer UTF-8 if the client supports it.
    for charset in charsets:
        if charset.lower().replace('_', '-') in ['utf8', 'utf-8']:
            return const.CHARSET_UTF8

    # Otherwise, look for a requested charset that Python supports.
    for charset in charsets:
        try:
            'xyz'.encode(charset, 'replace')  # test if charset is known
            return charset
        except:
            continue

    # If Python doesn't know any of the requested charsets, use UTF-8.
    return const.CHARSET_UTF8

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
        if config.get_for_repo(repo, 'deactivated'):
            continue
        titles = config.get_for_repo(repo, 'repo_titles', {})
        default_title = (titles.values() or ['?'])[0]
        title = titles.get(lang, titles.get('en', default_title))
        url = utils.get_repo_url(request, repo)
        test_mode = config.get_for_repo(repo, 'test_mode')
        options.append(utils.Struct(repo=repo, title=title, url=url,
                                    test_mode=test_mode))
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

def get_hidden_input_tags_for_preserved_query_params(request):
    """Gets HTML with <input type="hidden"> tags to preserve query parameters
    listed in utils.PRESERVED_QUERY_PARAM_NAMES e.g. "ui"."""
    tags_str = ''
    for name in utils.PRESERVED_QUERY_PARAM_NAMES:
        value = request.get(name)
        if value:
            tags_str += '<input type="hidden" name="%s" value="%s">\n' % (
                django.utils.html.escape(name),
                django.utils.html.escape(value))
    return tags_str

def setup_env(request):
    """Constructs the 'env' object, which contains various template variables
    that are commonly used by most handlers."""
    env = utils.Struct()
    env.repo, env.action = get_repo_and_action(request)
    env.config = config.Configuration(env.repo or '*')
    # TODO(ryok): Rename to local_test_mode or something alike to disambiguate
    # better from repository's test_mode.
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

    # Used for parsing query params. This must be done before accessing any
    # query params which may have multi-byte value, such as "given_name" below
    # in this function.
    request.charset = env.charset

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
    env.hidden_input_tags_for_preserved_query_params = (
        get_hidden_input_tags_for_preserved_query_params(request))

    ui_param = request.get('ui', '').strip().lower()

    # Interprets "small" and "style" parameters for backward compatibility.
    # TODO(ichikawa): Delete these in near future when we decide to drop
    # support of these parameters.
    small_param = request.get('small', '').strip().lower()
    style_param = request.get('style', '').strip().lower()
    if not ui_param and small_param == 'yes':
        ui_param = 'small'
    elif not ui_param and style_param:
        ui_param = style_param

    if ui_param:
        env.ui = ui_param
    elif user_agents.is_jp_tier2_mobile_phone(request):
        env.ui = 'light'
    else:
        env.ui = 'default'

    # UI configurations.
    #
    # Enables features which require JavaScript.
    env.enable_javascript = True
    # Enables operations which requires Captcha.
    env.enable_captcha = True
    # Enables photo upload.
    env.enable_photo_upload = True
    # Enables to flag/unflag notes as spam, and to reveal spam notes.
    env.enable_spam_ops = True
    # Enables duplicate marking mode.
    env.enable_dup_mode = True
    # Shows a logo on top of the page.
    env.show_logo = True
    # Shows language menu.
    env.show_language_menu = True
    # Uses short labels for buttons.
    env.use_short_buttons = False
    # Optional "target" attribute for links to non-small pages.
    env.target_attr = ''
    # Shows record IDs in the results page.
    env.show_record_ids_in_results = True

    if env.ui == 'small':
        env.show_logo = False
        env.target_attr = ' target="_blank" '

    elif env.ui == 'light':
        # Disables features which requires JavaScript. Some feature phones
        # doesn't support JavaScript.
        env.enable_javascript = False
        # Disables operations which requires Captcha because Captcha requires
        # JavaScript.
        env.enable_captcha = False
        # Uploading is often not supported in feature phones.
        env.enable_photo_upload = False
        # Disables spam operations because it requires JavaScript and
        # supporting more pages on ui=light.
        env.enable_spam_ops = False
        # Disables duplicate marking mode because it doesn't support
        # small screens and it requires JavaScript.
        env.enable_dup_mode = False
        # Hides the logo on the top to save the space. Also, the logo links
        # to the global page which doesn't support small screens.
        env.show_logo = False
        # Hides language menu because the menu in the current position is
        # annoying in feature phones.
        # TODO(ichikawa): Consider layout of the language menu.
        env.show_language_menu = False
        # Too long buttons are not fully shown in some feature phones.
        env.use_short_buttons = True
        # To make it simple.
        env.show_record_ids_in_results = False

    env.back_chevron = u'\xbb' if env.rtl else u'\xab'
    back_chevron_in_charset = True
    try:
        env.back_chevron.encode(env.charset)
    except UnicodeEncodeError:
        # u'\xbb' or u'\xab' is not in the charset (e.g. Shift_JIS).
        back_chevron_in_charset = False
    if not back_chevron_in_charset or env.ui == 'light':
        # Use ASCII characters on ui=light too because some feature phones
        # support UTF-8 but don't render UTF-8 symbols such as u'\xbb'.
        env.back_chevron = u'>>' if env.rtl else u'<<'

    # Repo-specific information.
    if env.repo:
        # repo_url is the root URL for the repository.
        env.repo_url = utils.get_repo_url(request, env.repo)
        # start_url is like repo_url but preserves parameters such as 'ui'.
        env.start_url = utils.get_url(request, env.repo, '')
        # URL of the link in the heading. The link on ui=small links to the
        # normal UI.
        env.repo_title_url = (
            env.repo_url if env.ui == 'small' else env.start_url)
        # URL to force default UI. Note that we show ui=light version in some
        # user agents when ui parameter is not specified.
        env.default_ui_url = utils.get_url(request, env.repo, '', ui='default')
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
        # If the repository is deactivated, we should not show test mode
        # notification.
        env.repo_test_mode = (
            env.config.test_mode and not env.config.deactivated)

        env.params_full_name = request.get('full_name', '').strip()
        if not env.params_full_name:
            # Preformat the name from 'given_name' and 'family_name' parameters.
            given_name = request.get('given_name', '').strip()
            family_name = request.get('family_name', '').strip()
            env.params_full_name = utils.get_full_name(
                given_name, family_name, env.config)

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
            response.set_status(404)
            response.out.write('Not found')
        else:
            # Serve a static page or file.
            env.robots_ok = True
            get_vars = lambda: {'env': env, 'config': env.config}
            content = resources.get_rendered(
                env.action, env.lang, (env.repo, env.charset), get_vars)
            if content is None:
                response.set_status(404)
                response.out.write('Not found')
            else:
                content_type, encoding = mimetypes.guess_type(env.action)
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
