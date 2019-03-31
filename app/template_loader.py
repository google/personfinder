import django.template
import django.template.loaders.base
import django.utils.translation


class TemplateLoader(django.template.loaders.base.Loader):
    """Our custom template loader, which loads templates from Resources."""

    def get_template(self, name, template_dirs=None, skip=None):
        import resources
        lang = django.utils.translation.get_language()  # currently active lang
        resource = resources.get_localized(name, lang)
        template = resource and resource.get_template()
        if template:
            return template
        else:
            raise django.template.TemplateDoesNotExist(name)

    def get_contents(self, origin):
        # Defining this method is necessary so that Django recognizes that
        # this loader is in the new format (using get_template() instead of
        # load_template()). But this method is actually not called when
        # get_template() is overridden.
        raise Exception('Not expected to be called')
