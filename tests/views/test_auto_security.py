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
import datetime
import os

import django.urls

import modelmodule.admin_acls as aa_model
import urls

import view_tests_base


# A tuple containing configuration for automatic security tests for a path.
PathTestInfoTuple = collections.namedtuple(
    'PathTestInfo',
    [
        # Whether the path is expected to accept GET requests.
        'accepts_get',
        # Whether the past is expected to accept POST requests.
        'accepts_post',
        # kwargs to use in generating the test path.
        'sample_path_kwargs',
        # The minimum admin level required to access the page (None if
        # non-admins are expected to be able to access it).
        'min_admin_level',
        # Whether POST requests should require an XSRF token.
        'requires_xsrf',
        # A dict with valid GET data, if required.
        'sample_get_data',
        # A dict with valid POST data, excluding an XSRF token (the tests will
        # add, or omit, the XSRF tokens).
        'sample_post_data',
        # The action ID used for XSRF tokens. Should be None if XSRF isn't used
        # for the page.
        'xsrf_action_id',
    ])


# pylint: disable=too-many-arguments
def path_test_info(
        accepts_get,
        accepts_post,
        min_admin_level,
        requires_xsrf,
        sample_path_kwargs=None,
        sample_get_data=None,
        sample_post_data=None,
        xsrf_action_id=None):
    """Generates a PathTestInfoTuple, with some default values."""
    return PathTestInfoTuple(
        accepts_get=accepts_get,
        accepts_post=accepts_post,
        min_admin_level=min_admin_level,
        requires_xsrf=requires_xsrf,
        sample_path_kwargs=sample_path_kwargs,
        sample_get_data=sample_get_data,
        sample_post_data=sample_post_data,
        xsrf_action_id=xsrf_action_id)


TEST_PERSON_RECORD_ID = 'testid123'


class AutoSecurityTests(view_tests_base.ViewTestsBase):
    """Tests that access restrictions are enforced."""
    # pylint: disable=no-self-use

    # A map from path names (defined in urls.py) to PathTestInfo tuples.
    PATH_TEST_INFO = {
        'admin_acls':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=aa_model.AdminPermission.AccessLevel.MANAGER,
            requires_xsrf=True,
            sample_post_data={
                'email_address': 'l@mib.gov',
                'expiration_date': '2019-04-25',
                'level': 'moderator',
            },
            xsrf_action_id='admin/acls'),
        'admin_apikeys-list':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=aa_model.AdminPermission.AccessLevel.SUPERADMIN,
            requires_xsrf=False),
        'admin_apikeys-manage':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=aa_model.AdminPermission.AccessLevel.SUPERADMIN,
            requires_xsrf=True,
            sample_post_data={
                'contact_name': 'Bob',
                'contact_email': 'bob@fridge.com',
                'organization_name': 'Vance Refrigeration',
            },
            xsrf_action_id='admin_api_keys'),
        'admin_create-repo':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            min_admin_level=aa_model.AdminPermission.AccessLevel.SUPERADMIN,
            requires_xsrf=True,
            sample_post_data={
                'new_repo': 'new-hampshire',
            },
            xsrf_action_id='admin/create_repo'),
        'admin_dashboard':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=aa_model.AdminPermission.AccessLevel.MANAGER,
            requires_xsrf=False),
        'admin_delete-record':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=aa_model.AdminPermission.AccessLevel.MODERATOR,
            requires_xsrf=True,
            sample_post_data={
                'id': 'abc123',
            },
            xsrf_action_id='admin/delete_record'),
        'admin_global-index':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            min_admin_level=aa_model.AdminPermission.AccessLevel.SUPERADMIN,
            requires_xsrf=True,
            sample_post_data={
                'feedback_url': 'www.example.com/feedback',
            },
            xsrf_action_id='admin/global-index'),
        'admin_repo-index':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=aa_model.AdminPermission.AccessLevel.MANAGER,
            requires_xsrf=True,
            sample_post_data={
                'custommsg__start_page_custom_htmls__en': 'custom message',
            },
            xsrf_action_id='admin/repo-index'),
        'admin_review':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=aa_model.AdminPermission.AccessLevel.MODERATOR,
            requires_xsrf=True,
            sample_post_data={
                'note.abc': 'accept',
            },
            xsrf_action_id='admin/review'),
        'admin_statistics':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            min_admin_level=aa_model.AdminPermission.AccessLevel.MANAGER,
            requires_xsrf=False),
        'enduser_global-index':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            min_admin_level=None,
            requires_xsrf=False),
        'enduser_global-index-altpath':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            min_admin_level=None,
            requires_xsrf=False),
        'enduser_global-index-altpath2':
            path_test_info(
                accepts_get=True,
                accepts_post=False,
                min_admin_level=None,
                requires_xsrf=False),
        'frontendapi_add-note':
        path_test_info(
            accepts_get=False,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=None,
            requires_xsrf=False,
            sample_post_data={
                'id': TEST_PERSON_RECORD_ID,
                'author_name': 'Mateo',
                'text': 'here is text',
            }),
        'frontendapi_create':
        path_test_info(
            accepts_get=False,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=None,
            requires_xsrf=False,
            sample_post_data={
                'given_name': 'Matt',
                'family_name': 'Matthews',
                'own_info': 'yes',
            }),
        'frontendapi_person':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=None,
            requires_xsrf=False,
            sample_get_data={'id': TEST_PERSON_RECORD_ID}),
        'frontendapi_repo':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=None,
            requires_xsrf=False),
        'frontendapi_results':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=None,
            requires_xsrf=False),
        'meta_sitemap':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            min_admin_level=None,
            requires_xsrf=False),
        'meta_static-files':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            sample_path_kwargs={
                'repo': 'haiti',
                'filename': 'facebook-16x16.png',
            },
            min_admin_level=None,
            requires_xsrf=False),
        'meta_static-howto':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            min_admin_level=None,
            requires_xsrf=False),
        'meta_static-responders':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            min_admin_level=None,
            requires_xsrf=False),
        'tasks_check-expired-person-records':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=None,
            requires_xsrf=False),
        'tasks_check-note-data-validity':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=None,
            requires_xsrf=False),
        'tasks_check-person-data-validity':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=None,
            requires_xsrf=False),
        'tasks_cleanup-stray-notes':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=None,
            requires_xsrf=False),
        'tasks_cleanup-stray-subscriptions':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=None,
            requires_xsrf=False),
        'tasks_process-expirations':
        path_test_info(
            accepts_get=True,
            accepts_post=True,
            sample_path_kwargs={'repo': 'haiti'},
            min_admin_level=None,
            requires_xsrf=False),
        'tasks_sitemap-ping':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            min_admin_level=None,
            requires_xsrf=False),
        'thirdparty-endpoints_repo-feed':
        path_test_info(
            accepts_get=True,
            accepts_post=False,
            sample_path_kwargs={'repo': 'global'},
            min_admin_level=None,
            requires_xsrf=False),
    }

    EXEMPT_PATHS = [
        # We exempt this from the auto-tests because it should normally (if
        # datastore is already set up) return an error, regardless of whether
        # the requester is an admin.
        'meta_setup-datastore',
    ]

    def init_testbed_stubs(self):
        """Initializes the App Engine testbed stubs.

        The base class initializes a Datastore stub, which seems to cause
        problems when we set another app ID (for the task tests). We don't
        really need Datastore for this, so just override the base class and
        stick to the user and memcache stubs.
        """
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()

    def setUp(self):
        super(AutoSecurityTests, self).setUp()
        self.data_generator.repo()
        self.data_generator.setup_repo_config()
        self.data_generator.person(
            record_id=TEST_PERSON_RECORD_ID,
            expiry_date=datetime.datetime(2090, 1, 1))

    def get_path(self, path_name):
        """Gets a path to use for the given path name.

        Args:
            path_name (str): The path name defined in urls.py.

        This will first try to reverse the URL with no arguments, and then fall
        back to reversing it with a "repo" argument. If we ever have URLs with
        more interesting things in the path besides repo, we'll have to rethink
        this.
        """
        path_info = AutoSecurityTests.PATH_TEST_INFO[path_name]
        return django.urls.reverse(
            path_name, kwargs=path_info.sample_path_kwargs)

    def get_valid_post_data(self, path_info):
        """Gets data for a valid POST requests.

        Generates and includes a valid XSRF token when needed.
        """
        if path_info.requires_xsrf:
            # Copy the data dict to avoid mutating the original.
            data = copy.deepcopy(path_info.sample_post_data)
            data['xsrf_token'] = self.xsrf_token(path_info.xsrf_action_id)
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
                if filter_func(path_info) and not path_name.startswith('tasks')]

    def test_blocked_to_non_admins(self):
        """Tests that admin-only pages aren't available to non-admins."""
        self.login_as_nonadmin()
        for (path_name, path_info) in self.get_paths_to_test(
                lambda path_info: path_info.min_admin_level is not None):
            path = self.get_path(path_name)
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

    def _check_admin_blocking(self, level):
        levels = aa_model.AdminPermission.AccessLevel.ORDERING[
            aa_model.AdminPermission.AccessLevel.ORDERING.index(level)+1:]
        for (path_name, path_info) in self.get_paths_to_test(
                lambda path_info: path_info.min_admin_level in levels):
            path = self.get_path(path_name)
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

    def test_moderator_blocking(self):
        """Tests that moderators can't access manager/superadmin pages."""
        self.login_as_moderator()
        self._check_admin_blocking(
            aa_model.AdminPermission.AccessLevel.MODERATOR)

    def test_manager_blocking(self):
        """Tests that managers can't access superadmin pages."""
        self.login_as_manager()
        self._check_admin_blocking(aa_model.AdminPermission.AccessLevel.MANAGER)

    def _check_admin_accessing(self, level):
        levels = aa_model.AdminPermission.AccessLevel.ORDERING[
            :aa_model.AdminPermission.AccessLevel.ORDERING.index(level)+1]
        for (path_name, path_info) in self.get_paths_to_test(
                lambda path_info: path_info.min_admin_level in levels):
            path = self.get_path(path_name)
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

    def test_moderator_accessing(self):
        """Tests that moderators can access moderator pages."""
        self.login_as_moderator()
        self._check_admin_accessing(
            aa_model.AdminPermission.AccessLevel.MODERATOR)

    def test_manager_accessing(self):
        """Tests that managers can access manager/moderator pages."""
        self.login_as_manager()
        self._check_admin_accessing(
            aa_model.AdminPermission.AccessLevel.MANAGER)

    def test_superadmin_accessing(self):
        """Tests that superadmins can access all pages."""
        self.login_as_superadmin()
        self._check_admin_accessing(
            aa_model.AdminPermission.AccessLevel.SUPERADMIN)

    def test_other_pages_unrestricted(self):
        """Tests that non-admins can access unrestricted pages."""
        self.login_as_nonadmin()
        for (path_name, path_info) in self.get_paths_to_test(
                lambda path_info: path_info.min_admin_level is None):
            path = self.get_path(path_name)
            if path_info.accepts_get:
                resp = self.client.get(
                    path, data=path_info.sample_get_data, secure=True)
                self.assertEqual(
                    resp.status_code, 200,
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
        self.login_as_superadmin()
        for (path_name, path_info) in self.get_paths_to_test(
                lambda path_info: path_info.requires_xsrf):
            # Just in case someone accidentally included an XSRF token in the
            # PathTestInfo tuple.
            assert 'xsrf_token' not in path_info.sample_post_data
            path = self.get_path(path_name)
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
        self.login_as_superadmin()
        for (path_name, path_info) in self.get_paths_to_test(
                lambda path_info: path_info.requires_xsrf):
            path = self.get_path(path_name)
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
            if pattern.name in AutoSecurityTests.EXEMPT_PATHS:
                continue
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
            path = self.get_path(pattern.name)
            assert self.client.get(path, secure=True).status_code == 403
