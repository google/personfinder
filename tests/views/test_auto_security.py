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

import collections
import copy

import django.urls

import urls
import utils
import views

import view_tests_base

PathTestInfo = collections.namedtuple('PathTestInfo', [
    'accepts_get',
    'accepts_post',
    'restricted_to_admins',
    'requires_xsrf',
    'sample_post_data',
    'xsrf_action_id',
])


class AutoSecurityTests(view_tests_base.ViewTestsBase):
    """Tests that access restrictions are enforced."""

    PATH_TEST_INFO = {
        'admin-create-repo': PathTestInfo(
            accepts_get=True,
            accepts_post=True,
            restricted_to_admins=True,
            requires_xsrf=True,
            sample_post_data={
                'new_repo': 'new-hampshire',
            },
            xsrf_action_id='admin/create_repo'),
        'admin-statistics': PathTestInfo(
            accepts_get=True,
            accepts_post=False,
            restricted_to_admins=True,
            requires_xsrf=False,
            sample_post_data=None,
            xsrf_action_id=None),
    }

    def setUp(self):
        super(AutoSecurityTests, self).setUp()
        self.xsrf_tool = utils.XsrfTool()

    def get_valid_post_data(self, path_info):
        if path_info.requires_xsrf:
            # Copy the data dict to avoid mutating the original.
            data = copy.deepcopy(path_info.sample_post_data)
            data['xsrf_token'] = self.xsrf_tool.generate_token(
                view_tests_base.ViewTestsBase.TEST_USER_ID,
                path_info.xsrf_action_id)
            return data
        return path_info.sample_post_data

    def test_blocked_to_non_admins(self):
        """Tests that admin-only pages aren't available to non-admins."""
        self.login(is_admin=False)
        for (path_name, path_info
            ) in filter(lambda (_, path_info): path_info.restricted_to_admins,
                        AutoSecurityTests.PATH_TEST_INFO.items()):
            path = django.urls.reverse(path_name)
            if path_info.accepts_get:
                self.assertEqual(
                    self.client.get(path, secure=True).status_code,
                    403,
                    'Admin-only page available to non-admin: %s' % path_name)
            if path_info.accepts_post:
                self.assertEqual(
                    self.client.post(
                        path,
                        self.get_valid_post_data(path_info),
                        secure=True).status_code,
                    403,
                    'Admin-only page available to non-admin: %s' % path_name)

    def test_available_to_admins(self):
        """Tests that admin-only pages are available to admins.

        This is a sort of meta-test: I'm not really concerned that we might
        accidentally lock admins out of the admin pages, but I do want to make
        sure that the test above actually depends on the user not being an admin
        (as opposed to access getting denied because the tests are set up wrong
        somehow).
        """
        self.login(is_admin=True)
        for (path_name, path_info
            ) in filter(lambda (_, path_info): path_info.restricted_to_admins,
                        AutoSecurityTests.PATH_TEST_INFO.items()):
            path = django.urls.reverse(path_name)
            if path_info.accepts_get:
                self.assertEqual(
                    self.client.get(path, secure=True).status_code,
                    200,
                    'GET unavailable to admins for: %s' % path_name)
            # Some POST requests might return a redirect, so just ensure they
            # don't get a 403 like non-admins do.
            if path_info.accepts_post:
                self.assertNotEqual(
                    self.client.post(
                        path,
                        self.get_valid_post_data(path_info),
                        secure=True).status_code,
                    403,
                    'POST unavailable to admins for: %s' % path_name)

    def test_other_pages_unrestricted(self):
        """Tests that non-admins can access unrestricted pages."""
        self.login(is_admin=False)
        for (path_name, path_info
            ) in filter(lambda (_, path_info):
                        not path_info.restricted_to_admins,
                        AutoSecurityTests.PATH_TEST_INFO.items()):
            path = django.urls.reverse(path_name)
            if path_info.accepts_get:
                self.assertEqual(
                    self.client.get(path, secure=True).status_code,
                    200,
                    'Unrestricted page blocked to non-admin: %s' % path_name)
            if path_info.accepts_post:
                # Redirects are fine, just check that they don't get a 403.
                self.assertNotEqual(
                    self.client.post(
                        path,
                        self.get_valid_post_data(path_info),
                        secure=True).status_code,
                    403,
                    'Unrestricted page blocked to non-admin: %s' % path_name)

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
