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
import django.utils.decorators
import django.views

import config
import const
import resources
import site_settings
import utils


class BaseView(django.views.View):
    """Base view class shared across the app."""

    # This should be overridden by subclasses.
    ACTION_ID = None

    _GET_PARAMETERS = {
        'lang': utils.strip,
    }

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
        del request, args  # unused

        # Set up the parameters and read in the base set of parameters.
        self.params = utils.Struct()
        self.read_params(get_params=BaseView._GET_PARAMETERS)

        # Set up env variable with data needed by the whole app.
        self.env = utils.Struct()
        self.env.repo = kwargs.get('repo', None)
        self.env.action = self.ACTION_ID
        self.env.config = config.Configuration(self.env.repo or '*')
        # Django will make a guess about what language to use, but Django's
        # guess should be overridden by the lang CGI param if it's set.
        # TODO(nworden): figure out how much of the logic below we still need
        # now that Django can do a lot of the work for us.
        lang = self.params.get('lang') or self.request.LANGUAGE_CODE
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

    def read_params(self, get_params=None, post_params=None, file_params=None):
        """Reads CGI parameter values into self.params.

        Args:
            get_params (dict): A dictionary from GET parameter keys to validator
                functions.
            post_params (dict): A dictionary from POST parameter keys to
                validator functions.
            file_params (dict): A dictionary from POST parameter keys for
                uploaded files to validator functions.
        """
        if self.request.method == 'GET':
            if get_params:
                for key, validator in get_params.items():
                    if key in self.request.GET:
                        setattr(self.params, key,
                                validator(self.request.GET[key]))
        else:
            if post_params:
                for key, validator in post_params.items():
                    if key in self.request.POST:
                        setattr(self.params, key,
                                validator(self.request.POST[key]))
            if file_params:
                for key, validator in file_params.items():
                    if key in self.request.FILES:
                        setattr(self.params, key,
                                validator(self.request.FILES[key]))

    def _request_is_for_prefixed_path(self):
        """Checks if the request's path uses an optional path prefix."""
        if not site_settings.OPTIONAL_PATH_PREFIX:
            return False
        req_path = self.request.path[1:]  # drop the leading slash
        if req_path == site_settings.OPTIONAL_PATH_PREFIX:
            return True
        return req_path.startswith('%s/' % site_settings.OPTIONAL_PATH_PREFIX)

    def build_absolute_path(self, path=None):
        """Builds an absolute path, including the path prefix if required.

        Django's HttpRequest objects have a similar function, but we implement
        our own so that we can handle path prefixes correctly when they're in
        use.

        Args:
            path (str, optional): A path beginning with a slash (may include a
                query string), e.g., '/abc?x=y'. If the path argument is not
                specified or is None, the current request's path will be used.

        Returns:
            str: An absolute path, including the sitewide OPTIONAL_PATH_PREFIX
            if it was used with the original request (e.g.,
            '/personfinder/abc?x=y'). Does not preserve query parameters from
            the original request.
        """
        if path is None:
            # request.path will already include the path prefix if it's being
            # used.
            return self.request.path
        assert path[0] == '/'
        if self._request_is_for_prefixed_path():
            return '/%s%s' % (site_settings.OPTIONAL_PATH_PREFIX, path)
        else:
            return path

    def build_absolute_uri(self, path=None):
        """Builds an absolute URI given a path.

        See build_absolute_path (above) for an explanation of why we implement
        this function ourselves.

        Args:
            path (str, optional): A path beginning with a slash (may include a
                query string), e.g., '/abc?x=y'. If the path argument is not
                specified or is None, the current request's path will be used.

        Returns:
            str: An absolute URI, including the sitewide OPTIONAL_PATH_PREFIX if
            it was used with the original request (e.g.,
            'http://localhost:8000/personfinder/abc?x=y'). Does not preserve
            query parameters from the original request.
        """
        return self.request.build_absolute_uri(self.build_absolute_path(path))

    def render(self, template_name, **template_vars):
        """Renders a template with the given variables.

        Args:
            template_name (str): The filename of the template in app/resources.
            **template_vars: Named variables to pass to the template.

        Returns:
            HttpResponse: An HttpResponse with the rendered template.
        """

        def get_vars():
            """A function returning vars, for use by the resources module."""
            template_vars['env'] = self.env
            # TODO(nworden): change templates to access config through env, which
            # already has the config anyway
            template_vars['config'] = self.env.config
            template_vars['params'] = self.params
            return template_vars

        query_str = self.request.META.get('QUERY_STRING', '')
        extra_key = (self.env.repo, self.env.charset, query_str)
        return django.http.HttpResponse(
            resources.get_rendered(template_name, self.env.lang, extra_key,
                                   get_vars, 0))

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
