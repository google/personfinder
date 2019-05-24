# Copyright 2019 Google Inc.
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
"""View-related code common to the whole app."""

import functools
import re

import django.http
import django.shortcuts
import django.utils.decorators
import django.views
import six.moves.urllib.parse as urlparse

import config
import const
import site_settings
import user_agents
import utils


class Params(object):
    """An object containing values of CGI params."""

    def __init__(self, request):
        self._request = request
        self._values = {}

    def __getattr__(self, name):
        return self._values.get(name, None)

    def get(self, name, default=None):
        """Gets a value, or falls back to the given default."""
        return self._values.get(name, default)

    def put(self, name, value):
        """Adds a value."""
        self._values.put(name, value)

    def read_values(self, get_params=None, post_params=None, file_params=None):
        """Reads params with the given keys and validators.

        Each of get_params, post_params, and file_params should be a map of CGI
        param keys to validator functions. If the key is present, the value will
        be passed to the validator and the output stored in the Params object;
        otherwise it will store None for the key's value.
        """
        if self._request.method == 'GET':
            if get_params:
                for key, validator in get_params.items():
                    if key in self._request.GET:
                        self._values[key] = validator(self._request.GET[key])
        elif self._request.method == 'POST':
            if post_params:
                for key, validator in post_params.items():
                    if key in self._request.POST:
                        self._values[key] = validator(self._request.POST[key])
            if file_params:
                for key, validator in file_params.items():
                    if key in self._request.FILES:
                        self._values[key] = validator(self._request.FILES[key])


class BaseView(django.views.View):
    """Base view class shared across the app."""

    # This should be overridden by subclasses.
    ACTION_ID = None

    class Env(object):
        """Class to store environment information used by views and templates.

        Subclasses of BaseView may define their own Env class (which must be
        subclasses of BaseView.Env); that Env class (as long as it's called
        "Env") will be used automatically when the env is set up.
        """
        # pylint: disable=attribute-defined-outside-init
        # pylint: disable=too-many-instance-attributes

        @property
        def action(self):
            """Gets the action ID, an identifier for the page being served."""
            return self._action

        @action.setter
        def action(self, value):
            self._action = value

        @property
        def charset(self):
            """Gets the character encoding being used to serve the page."""
            return self._charset

        @charset.setter
        def charset(self, value):
            self._charset = value

        @property
        def config(self):
            """Gets the config, a config.Config object for the repository."""
            return self._config

        @config.setter
        def config(self, value):
            self._config = value

        @property
        def enable_javascript(self):
            "Gets whether or not to enable JavaScript." ""
            return self._enable_javascript

        @enable_javascript.setter
        def enable_javascript(self, value):
            self._enable_javascript = value

        @property
        def fixed_static_url_base(self):
            """Gets the base URL for fixed static files."""
            return self._fixed_static_url_base

        @fixed_static_url_base.setter
        def fixed_static_url_base(self, value):
            self._fixed_static_url_base = value

        @property
        def global_url(self):
            """Gets the URL for the global root."""
            return self._global_url

        @global_url.setter
        def global_url(self, value):
            self._global_url = value

        @property
        def lang(self):
            """Gets the code for the language being used (see const.py)."""
            return self._lang

        @lang.setter
        def lang(self, value):
            self._lang = value

        @property
        def repo(self):
            """Gets the repository ID, or None if it's a global page."""
            return self._repo

        @repo.setter
        def repo(self, value):
            self._repo = value

        @property
        def repo_url(self):
            """Gets the URL for the repo root."""
            return self._repo_url

        @repo_url.setter
        def repo_url(self, value):
            self._repo_url = value

        @property
        def rtl(self):
            """Gets whether the language is a right-to-left language."""
            return self._rtl

        @rtl.setter
        def rtl(self, value):
            self._rtl = value

        @property
        def show_logo(self):
            """Gets whether or not to show the logo in the header."""
            return self._show_logo

        @show_logo.setter
        def show_logo(self, value):
            self._show_logo = value

        @property
        def ui(self):
            """Gets the UI mode to use."""
            return self._ui

        @ui.setter
        def ui(self, value):
            self._ui = value

    def setup(self, request, *args, **kwargs):
        """Sets up the handler.

        Views aren't passed any request-specific information when they're
        initialized, so you can't really do much in __init__. However, having a
        function that gets called before dispatch is useful for all kinds of
        things (in particular, it's useful to have a top-down function, where
        the parent class functions run before those of subclasses). setup() is
        essentially a substitute for __init__().

        Args:
            request (HttpRequest): The request object.
            *args: Unused.
            **kwargs: Arbitrary keyword arguments. Should include repository ID
                (under the key 'repo') if applicable.
        """
        # pylint: disable=attribute-defined-outside-init
        # TODO(nworden): don't forget to call super.setup here once we upgrade
        # to Django 2.2.
        del args  # unused

        # Set up the parameters and read in the base set of parameters.
        self.params = Params(self.request)
        self.params.read_values(
            get_params={
                'lang': utils.strip,
                'ui': utils.strip,
            },
            post_params={
                'lang': utils.strip,
            })

        # Set up env variable with data needed by the whole app.
        self.env = self.Env()
        self.env.repo = kwargs.get('repo', None)
        self.env.action = self.ACTION_ID
        self.env.config = config.Configuration(self.env.repo or '*')
        # Django will make a guess about what language to use, but Django's
        # guess should be overridden by the lang CGI param if it's set.
        # TODO(nworden): figure out how much of the logic below we still need
        # now that Django can do a lot of the work for us.
        lang = self.params.lang or self.request.LANGUAGE_CODE
        lang = re.sub('[^A-Za-z0-9-]', '', lang)
        lang = const.LANGUAGE_SYNONYMS.get(lang, lang)
        if lang in const.LANGUAGE_ENDONYMS.keys():
            self.env.lang = lang
        else:
            self.env.lang = (self.env.config.language_menu_options[0]
                             if self.env.config.language_menu_options else
                             const.DEFAULT_LANGUAGE_CODE)
        self.env.rtl = self.env.lang in const.LANGUAGES_BIDI
        self.env.charset = const.CHARSET_UTF8
        # TODO(nworden): try to eliminate use of global_url. It doesn't seem
        # great that templates are building URLs by sticking things onto this.
        self.env.global_url = self.build_absolute_uri('/global')
        self.env.repo_url = self.build_absolute_uri('/', self.env.repo)
        self.env.fixed_static_url_base = self.build_absolute_uri('/static')
        if self.params.ui:
            self.env.ui = self.params.ui
        elif user_agents.prefer_lite_ui(request):
            self.env.ui = 'light'
        else:
            self.env.ui = 'default'
        self.env.enable_javascript = self.env.ui
        self.env.show_logo = self.env.ui == 'default'

    def _request_is_for_prefixed_path(self):
        """Checks if the request's path uses an optional path prefix."""
        if not site_settings.OPTIONAL_PATH_PREFIX:
            return False
        req_path = self.request.path[1:]  # drop the leading slash
        if req_path == site_settings.OPTIONAL_PATH_PREFIX:
            return True
        return req_path.startswith('%s/' % site_settings.OPTIONAL_PATH_PREFIX)

    def build_absolute_path(self, path=None, repo=None, params=None):
        """Builds an absolute path, including the path prefix if required.

        Django's HttpRequest objects have a similar function, but we implement
        our own so that we can handle path prefixes correctly when they're in
        use.

        Args:
            path (str, optional): A path beginning with a slash (may include a
                query string), e.g., '/abc?x=y'. If the path argument is not
                specified or is None, the current request's path will be used.
            repo (str, optional): A repo ID. If specified, the path will be
                considered relative to the repo's route. If this is specified,
                path must also be specified.
            params (list, optional): A list of tuples of query param keys and
                values to add to the path.

        Returns:
            str: An absolute path, including the sitewide OPTIONAL_PATH_PREFIX
            if it was used with the original request (e.g.,
            '/personfinder/abc?x=y'). Does not preserve query parameters from
            the original request.
        """
        if path is None:
            assert not repo
            # request.path will already include the path prefix if it's being
            # used.
            return self.request.path
        assert path[0] == '/'
        if repo:
            path = '/%s%s' % (repo, path)
        if self._request_is_for_prefixed_path():
            res = '/%s%s' % (site_settings.OPTIONAL_PATH_PREFIX, path)
        else:
            res = path
        if params:
            url_parts = list(urlparse.urlparse(res))
            url_params = dict(urlparse.parse_qsl(url_parts[4]))
            for key, value in params:
                if value is None:
                    if key in url_params:
                        del(url_params[key])
                else:
                    url_params[key] = value
            url_parts[4] = utils.urlencode(url_params)
            res = urlparse.urlunparse(url_parts)
        return res

    def build_absolute_uri(self, path=None, repo=None, params=None):
        """Builds an absolute URI given a path.

        See build_absolute_path (above) for an explanation of why we implement
        this function ourselves.

        Args:
            path (str, optional): A path beginning with a slash (may include a
                query string), e.g., '/abc?x=y'. If the path argument is not
                specified or is None, the current request's path will be used.
            repo (str, optional): A repo ID. If specified, the path will be
                considered relative to the repo's route. If this is specified,
                path must also be specified.
            params (list, optional): A list of tuples of query param keys and
                values to add to the path.

        Returns:
            str: An absolute URI, including the sitewide OPTIONAL_PATH_PREFIX if
            it was used with the original request (e.g.,
            'http://localhost:8000/personfinder/abc?x=y'). Does not preserve
            query parameters from the original request.
        """
        return self.request.build_absolute_uri(
            self.build_absolute_path(path, repo, params))

    def render(self, template_name, status_code=200, **template_vars):
        """Renders a template with the given variables.

        Args:
            template_name (str): The filename of the template in app/resources.
            **template_vars: Named variables to pass to the template.

        Returns:
            HttpResponse: An HttpResponse with the rendered template.
        """
        template_name = '%s.template' % template_name
        context = {
            'env': self.env,
            # TODO(nworden): change templates to access config through env,
            # which already has the config anyway
            'config': self.env.config,
            'params': self.params,
            'csp_nonce': self.request.csp_nonce,
        }
        context.update(template_vars)
        return django.shortcuts.render(
            self.request, template_name, context, status=status_code)

    def error(self, status_code, message=''):
        """Returns an error response.

        Args:
            status_code (int): The HTTP status code to use.
            message (str, optional): A message to display. Defaults to the empty
                string.

        Returns:
            HttpResponse: An HTTP response with the given status code and
            message.
        """
        # pylint: disable=no-self-use
        # Making this a method of BaseView keeps it consistent with render(),
        # and probably other similar functions in the future.
        return django.http.HttpResponse(
            content=message, content_type='text/plain', status=status_code)

    @django.utils.decorators.classonlymethod
    def as_view(cls, **initkwargs):
        # pylint: disable=E,W,R,C
        # We want to have a setup() function called before dispatch() (see
        # explanation in the comments on the setup() function), and Django 2.2
        # has support for it built in. However, we're not on Django 2.2 yet, so
        # we make the modification to View.as_view() ourselves to get this
        # feature ahead of time (the code below is just a copy of the original
        # Django 1.11 View.as_view function, with the setup() call stuck in). We
        # can clean this up when we upgrade to Django 2.2.
        """Main entry point for a request-response process."""
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that." %
                                (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError(
                    "%s() received an invalid keyword %r. as_view "
                    "only accepts arguments that are already "
                    "attributes of the class." % (cls.__name__, key))

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get
            self.request = request
            self.args = args
            self.kwargs = kwargs
            self.setup(request, *args, **kwargs)
            return self.dispatch(request, *args, **kwargs)

        view.view_class = cls
        view.view_initkwargs = initkwargs

        # take name and docstring from class
        functools.update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        functools.update_wrapper(view, cls.dispatch, assigned=())
        return view
