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
