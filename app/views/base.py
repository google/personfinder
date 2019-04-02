import django.http
import django.utils.decorators
import django.views
import functools

import config
import const
import resources
import site_settings
import utils


class BaseView(django.views.View):

    _GET_PARAMETERS = {
        'lang': utils.strip,
    }

    def setup(self, request, *args, **kwargs):
        # TODO(nworden): don't forget to call super.setup here once we upgrade
        # to Django 2.2.

        # Set up the parameters and read in the base set of parameters.
        self.params = utils.Struct()
        self.read_params(get_params=BaseView._GET_PARAMETERS)

        # Set up env variable with data needed by the whole app.
        self.env = utils.Struct()
        self.env.repo = kwargs.get('repo', None)
        self.env.action = kwargs['action']
        self.env.config = config.Configuration(self.env.repo or '*')
        self.env.lang = self.params.lang
        self.env.rtl = self.env.lang in const.LANGUAGES_BIDI
        self.env.charset = const.CHARSET_UTF8
        # TODO(nworden): try to eliminate use of global_url. It doesn't seem
        # great that templates are building URLs by sticking things onto this.
        self.env.global_url = self.build_absolute_uri('global')

    def read_params(self, get_params={}, post_params={}, file_params={}):
        """Reads CGI parameter values into self.params.

        Args:
            get_params (dict): A dictionary from GET parameter keys to validator
                functions.
            post_params (dict): A dictionary from POST parameter keys to
                validator functions.
            file_params (dict): A dictionary from FILES parameter keys to
                validator functions.
        """
        if self.request.method == 'GET':
            for key, validator in get_params.items():
                if key in self.request.GET:
                    setattr(self.params, key, validator(self.request.GET[key]))
        else:
            for key, validator in post_params.items():
                if key in self.request.POST:
                    setattr(self.params, key, validator(self.request.POST[key]))
            for key, validator in file_params.items():
                if key in self.request.FILES:
                    setattr(self.params, key,
                            validator(self.request.FILES[key]))

    def build_absolute_path(self, path=None):
        """Builds an absolute path given a path.

        Django's HttpRequest objects have a similar function, but we implement
        our own so that we can handle path prefixes correctly when they're in
        use.

        Args:
            path (str, optional): A path, e.g., 'abc?x=y'. Must NOT have a
                leading slash. May include a query string. If not specified,
                will return the current path.

        Returns:
            str: An absolute path, including the sitewide OPTIONAL_PATH_PREFIX
            if it was used with the original request (e.g.,
            '/personfinder/abc?x=y').
        """
        if path is None:
            return self.request.get_full_path()
        prefix = (site_settings.OPTIONAL_PATH_PREFIX if
                  self.request.path_info[1:].startswith(
                      site_settings.OPTIONAL_PATH_PREFIX)
                  else '')
        return '/%s%s' % (prefix, path)

    def build_absolute_uri(self, path=None):
        """Builds an absolute URI given a path.

        See build_absolute_path (above) for an explanation of why we implement
        this function ourselves.

        Args:
            path (str, optional): A path, e.g., 'abc?x=y'. Must NOT have a
                leading slash. May include a query string. If not specified,
                will use the current path.

        Returns:
            str: An absolute URI, including the sitewide OPTIONAL_PATH_PREFIX if
            it was used with the original request (e.g.,
            'http://localhost:8000/personfinder/abc?x=y').
        """
        return self.request.build_absolute_uri(self.build_absolute_path(path))

    def render(self, template_name, **template_vars):
        """Renders a template with the given variables.

        Args:
            template_name (str): The filename of the template in app/resources.
            **template_vars: Named variables to pass to the template.

        Returns:
            HttpResponse: A HttpResponse with the rendered template.
        """
        def get_vars():
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
        # Django discourages overriding View.__init__, but having a function
        # called before dispatch is useful for all sorts of things. Django 2.2
        # has support for a setup() hook that's called automatically before
        # dispatch, and I don't want to wait to use it, so we make the
        # modifications to View.as_view() ourselves to get this feature ahead of
        # time (this is just a copy of the original View.as_view function, with
        # the setup() call stuck in). We can clean this up when we upgrade to
        # Django 2.2.
        """
        Main entry point for a request-response process.
        """
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError("%s() received an invalid keyword %r. as_view "
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
