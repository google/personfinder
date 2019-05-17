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

"""Configurable static files.

We have static files and "static" files. The truly static files (e.g., the
hamburger menu icon or back button) are served directly out of
resources/static/fixed. The "static" files, configurable by the site admins, are
served by this view.
"""

import collections

import django.http

import resources
import views.base


ConfigurableStaticFile = collections.namedtuple(
    'ConfigurableStaticFile',
    [
        'content_type',
    ])


CONFIGURABLE_STATIC_FILES = {
    'facebook-16x16.png': ConfigurableStaticFile(content_type='image/png'),
    'linkedin-16x16.png': ConfigurableStaticFile(content_type='image/png'),
    'logo.png': ConfigurableStaticFile(content_type='image/png'),
    'twitter-16x16.png': ConfigurableStaticFile(content_type='image/png'),
}


class ConfigurableStaticFileView(views.base.BaseView):
    """The view for configurable static files."""

    ACTION_ID = 'static'

    def get(self, request, *args, **kwargs):
        """Serves get requests with configurable static files."""
        del request, args  # unused
        filename = kwargs['filename']
        if filename not in CONFIGURABLE_STATIC_FILES:
            return self.error(404)
        fileinfo = CONFIGURABLE_STATIC_FILES[filename]
        return django.http.HttpResponse(
            resources.get_rendered(
                'static/configurable/%s' % filename, self.env.lang),
            content_type=fileinfo.content_type)
