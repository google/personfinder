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

import view_tests_base

PathTestInfo = namedtuple('PathTestInfo', [
    'accepts_get',
    'accepts_post',
    'restricted_to_admins',
    'sample_xsrf_data',
])


class AutoSecurityTests(view_tests_base.ViewTestsBase):
    """Tests that access restrictions are enforced."""

    PATH_TEST_INFO = {
        'admin-create-repo':
        PathTestInfo(
            'accepts_get' =True,
            'accepts_post' =True,
            'restricted_to_admins' =True,
            'sample_xsrf_data' ={
                'new_repo': 'new-hampshire',
            }),
        'admin-statistics':
        PathTestInfo(
            'accepts_get' =True,
            'accepts_post' =False,
            'restricted_to_admins' =True,
            'sample_xsrf_data' =None,
        ),
    }

    # Dictionary from path name to a boolean indicating whether the page should
    # be restricted to admins.
    IS_RESTRICTED_TO_ADMINS = {
        'admin-create-repo': True,
        'admin-statistics': True,
    }

    def test_blocked_to_non_admins(self):
        """Tests that admin-only pages aren't available to non-admins."""
        self.login(is_admin=False)
        for (path_name, path_info
            ) in filter(lambda (_, path_info): path_info.restricted_to_admins,
                        AutoSecurityTests.PATH_TEST_INFO.items()):
            path = django.urls.reverse(path_name)
            if path_info.accepts_get:
                assert self.client.get(path, secure=True).status_code == 403
            if path_info.accepts_post:
                assert self.client.post(path, secure=True).status_code == 403

    def test_available_to_admins(self):
        """Tests that admin-only pages are available to admins.

        This is a sort of meta-test: I'm not really concerned that we might
        accidentally lock admins out of the admin pages, but I do want to make
        sure that the test above actually depends on the user not being an admin
        (as opposed to access getting denied because the tests are set up wrong
        somehow).
        """
        self.login(is_admin=True)
        for (path_name, _
            ) in filter(lambda item: item[1],
                        AccessRestrictionTests.IS_RESTRICTED_TO_ADMINS.items()):
            path = django.urls.reverse(path_name)
            assert self.client.get(path, secure=True).status_code == 200
            # Don't test POST requests here; they'll need an XSRF token and
            # that'll be covered in a separate test.

    def test_other_pages_unrestricted(self):
        """Tests that non-admins can access unrestricted pages."""
        self.login(is_admin=False)
        for (path_name, _
            ) in filter(lambda item: not item[1],
                        AccessRestrictionTests.IS_RESTRICTED_TO_ADMINS.items()):
            path = django.urls.reverse(path_name)
            assert self.client.get(path, secure=True).status_code != 403

    def test_all_paths_included(self):
        """Tests that all (Django-served) pages are listed.

        We want to make sure no one forgets to add these tests for admin pages,
        so we require that each URL path is included in the dictionary above.
        """
        for pattern in urls.urlpatterns:
            if pattern.name.startswith('prefixed:'):
                # Skip these; they're the same views as the non-prefixed
                # versions.
                continue
            assert (pattern.name in AutoSecurityTests.PATH_TEST_INFO)
