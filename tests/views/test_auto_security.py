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

"""Automatic security tests.

This file isn't meant for tests specific to a particular page; they're designed
as general-purpose tests for common security requirements. All paths must be
included in the AutoSecurityTests.PATH_TEST_INFO list (this is tested to ensure
we can't forget these tests for a new view).
"""

import collections
import copy
import os

import django.urls

import urls
import utils

import view_tests_base


# A tuple containing configuration for automatic security tests for a path.
PathTestInfo = collections.namedtuple(
    'PathTestInfo',
    [
        # Whether the path is expected to accept GET requests.
        'accepts_get',
        # Whether the past is expected to accept POST requests.
        'accepts_post',
        # Whether the page is restricted to admins.
        'restricted_to_admins',
        # Whether POST requests should require an XSRF token.
        'requires_xsrf',
        # A dict with valid POST data, excluding an XSRF token (the tests will
        # add, or omit, the XSRF tokens). Should be None if XSRF isn't used for
        # the page.
        'sample_post_data',
        # The action ID used for XSRF tokens. Should be None if XSRF isn't used
        # for the page.
        'xsrf_action_id',
    ])


class AutoSecurityTests(view_tests_base.ViewTestsBase):
    """Tests that access restrictions are enforced."""
    # pylint: disable=no-self-use

    # A map from path names (defined in urls.py) to PathTestInfo tuples.
    PATH_TEST_INFO = {
        'admin_create-repo':
        PathTestInfo(
            accepts_get=True,
            accepts_post=True,
            restricted_to_admins=True,
            requires_xsrf=True,
            sample_post_data={
                'new_repo': 'new-hampshire',
            },
            xsrf_action_id='admin/create_repo'),
        'admin_statistics':
        PathTestInfo(
            accepts_get=True,
            accepts_post=False,
            restricted_to_admins=True,
            requires_xsrf=False,
            sample_post_data=None,
            xsrf_action_id=None),
        'meta_sitemap':
        PathTestInfo(
            accepts_get=True,
            accepts_post=False,
            restricted_to_admins=False,
            requires_xsrf=False,
            sample_post_data=None,
            xsrf_action_id=None),
    }

    def setUp(self):
        super(AutoSecurityTests, self).setUp()
        self.xsrf_tool = utils.XsrfTool()

    def get_valid_post_data(self, path_info):
        """Gets data for a valid POST requests.

        Generates and includes a valid XSRF token when needed.
        """
        if path_info.requires_xsrf:
            # Copy the data dict to avoid mutating the original.
            data = copy.deepcopy(path_info.sample_post_data)
            data['xsrf_token'] = self.xsrf_tool.generate_token(
                view_tests_base.ViewTestsBase.TEST_USER_ID,
                path_info.xsrf_action_id)
            return data
        return path_info.sample_post_data

    def get_paths_to_test(self, filter_func):
        """Gets paths to test based on a filter function.

        Args:
            filter_func (function): A function that accepts a PathTestInfo tuple
            and returns True or False to indicate if it should be included.

        Returns:
            list: A list of tuples with path names and PathTestInfo tuples.
        """
        return [(path_name, path_info)
                for (path_name,
                     path_info) in AutoSecurityTests.PATH_TEST_INFO.items()
                if filter_func(path_info)]

    def test_blocked_to_non_admins(self):
        """Tests that admin-only pages aren't available to non-admins."""
        self.login(is_admin=False)
        for (path_name, path_info) in self.get_paths_to_test(
                lambda path_info: path_info.restricted_to_admins):
            path = django.urls.reverse(path_name)
            if path_info.accepts_get:
                self.assertEqual(
                    self.client.get(path, secure=True).status_code, 403,
                    'Admin-only page available to non-admin: %s' % path_name)
            if path_info.accepts_post:
                self.assertEqual(
                    self.client.post(
                        path, self.get_valid_post_data(path_info),
                        secure=True).status_code, 403,
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
        for (path_name, path_info) in self.get_paths_to_test(
                lambda path_info: path_info.restricted_to_admins):
            path = django.urls.reverse(path_name)
            if path_info.accepts_get:
                self.assertEqual(
                    self.client.get(path, secure=True).status_code, 200,
                    'GET unavailable to admins for: %s' % path_name)
            # Some POST requests might return a redirect, so just ensure they
            # don't get a 403 like non-admins do.
            if path_info.accepts_post:
                self.assertNotEqual(
                    self.client.post(
                        path, self.get_valid_post_data(path_info),
                        secure=True).status_code, 403,
                    'POST unavailable to admins for: %s' % path_name)

    def test_other_pages_unrestricted(self):
        """Tests that non-admins can access unrestricted pages."""
        self.login(is_admin=False)
        for (path_name, path_info) in self.get_paths_to_test(
                lambda path_info: not path_info.restricted_to_admins):
            path = django.urls.reverse(path_name)
            if path_info.accepts_get:
                self.assertEqual(
                    self.client.get(path, secure=True).status_code, 200,
                    'Unrestricted page blocked to non-admin: %s' % path_name)
            if path_info.accepts_post:
                # Redirects are fine, just check that they don't get a 403.
                self.assertNotEqual(
                    self.client.post(
                        path, self.get_valid_post_data(path_info),
                        secure=True).status_code, 403,
                    'Unrestricted page blocked to non-admin: %s' % path_name)

    def test_missing_xsrf_token(self):
        """Tests that, if XSRF is required, POSTs without a token are rejected.
        """
        self.login(is_admin=True)
        for (path_name, path_info) in self.get_paths_to_test(
                lambda path_info: path_info.requires_xsrf):
            # Just in case someone accidentally included an XSRF token in the
            # PathTestInfo tuple.
            assert 'xsrf_token' not in path_info.sample_post_data
            path = django.urls.reverse(path_name)
            self.assertEqual(
                self.client.post(path, path_info.sample_post_data,
                                 secure=True).status_code, 403,
                'XSRF page accepts data missing XSRF token: %s' % path_name)
            post_data = copy.deepcopy(path_info.sample_post_data)
            post_data['xsrf_token'] = ''
            self.assertEqual(
                self.client.post(path, post_data, secure=True).status_code, 403,
                'XSRF page accepts data empty XSRF token: %s' % path_name)

    def test_invalid_xsrf_token(self):
        """Tests that XSRF tokens are checked for validity."""
        self.login(is_admin=True)
        for (path_name, path_info) in self.get_paths_to_test(
                lambda path_info: path_info.requires_xsrf):
            path = django.urls.reverse(path_name)
            post_data = copy.deepcopy(path_info.sample_post_data)
            post_data['xsrf_token'] = 'NotAValidToken'
            self.assertEqual(
                self.client.post(path, post_data, secure=True).status_code, 403,
                'XSRF page accepts data invalid XSRF token: %s' % path_name)

    def test_all_paths_included(self):
        """Tests that all (Django-served) pages are listed.

        We want to make sure no one forgets to add these tests for admin pages,
        so we require that each URL path is included in the dictionary above.
        """
        for pattern in urls.urlpatterns:
            if pattern.name.startswith('prefixed__'):
                # Skip these; they're the same views as the non-prefixed
                # versions.
                continue
            if pattern.name.startswith('tasks_'):
                # Skip tasks; they'll be tested separately.
                continue
            assert pattern.name in AutoSecurityTests.PATH_TEST_INFO

    def test_gae_task_header_required(self):
        """Tests that tasks can only be called by App Engine.

        App Engine sets a special header (and strips it out of external
        requests); we use that to reject external requests to task handlers.
        """
        # Set this to a non-dev ID, because we permit non-GAE requests in dev.
        os.environ['APPLICATION_ID'] = 'prod-app'
        for pattern in urls.urlpatterns:
            if pattern.name.startswith('prefixed__'):
                # Skip these; they're the same views as the non-prefixed
                # versions.
                continue
            if not pattern.name.startswith('tasks_'):
                # Skip views that aren't task handlers; they're tested
                # elsewhere.
                continue
            path = django.urls.reverse(pattern.name)
            assert self.client.get(path, secure=True).status_code == 403
