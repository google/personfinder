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
"""Access restriction tests."""

import django.urls

import urls
import views

import django_tests_base


class AccessRestrictionTests(django_tests_base.DjangoTestsBase):

    # Dictionary from path name to a boolean indicating whether the page should
    # be restricted to admins.
    IS_RESTRICTED_TO_ADMINS = {
        'admin-statistics': True,
    }

    def test_blocked_to_non_admins(self):
        self.login(is_admin=False)
        for (path_name, _
            ) in filter(lambda item: item[1],
                        AccessRestrictionTests.IS_RESTRICTED_TO_ADMINS.items()):
            path = django.urls.reverse(path_name)
            assert self.client.get(path).status_code == 403
            assert self.client.post(path).status_code == 403

    def test_available_to_admins(self):
        self.login(is_admin=True)
        for (path_name, _
            ) in filter(lambda item: item[1],
                        AccessRestrictionTests.IS_RESTRICTED_TO_ADMINS.items()):
            path = django.urls.reverse(path_name)
            assert self.client.get(path).status_code == 200
            # Don't test POST requests here; they'll need an XSRF token and
            # that'll be covered in a separate test.

    def test_all_paths_included(self):
        for pattern in urls.urlpatterns:
            if pattern.name.startswith('prefixed:'):
                # Skip these; they're the same views as the non-prefixed
                # versions.
                continue
            assert (
                pattern.name in AccessRestrictionTests.IS_RESTRICTED_TO_ADMINS)
