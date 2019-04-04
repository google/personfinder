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

"""URL routing module."""

from django.conf import urls

import site_settings
import views.admin.statistics

# We include an optional trailing slash in all the patterns (Django has support
# for automatic redirection, but we don't want to send people redirect responses
# if it's not really needed).
_BASE_URL_PATTERNS = [(r'global/admin/statistics/?',
                       views.admin.statistics.AdminStatisticsView.as_view)]

# pylint: disable=invalid-name
# Pylint would prefer that this name be uppercased, but Django's going to look
# for this value in the urls module; it has to be called urlpatterns.
urlpatterns = [
    urls.url('^(%s)$' % path_exp, view_func())
    for (path_exp, view_func) in _BASE_URL_PATTERNS
]

if site_settings.OPTIONAL_PATH_PREFIX:
    urlpatterns += [
        urls.url(
            '^(%s)/(%s)$' % (site_settings.OPTIONAL_PATH_PREFIX, path_exp),
            view_func()) for (path_exp, view_func) in _BASE_URL_PATTERNS
    ]
