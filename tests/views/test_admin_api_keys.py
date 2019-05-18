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


"""Tests for the admin API keys pages."""

import django.http

import model

import view_tests_base


class ApiKeyListViewTests(view_tests_base.ViewTestsBase):
    """Tests the admin API keys list view."""

    def setUp(self):
        super(ApiKeyListViewTests, self).setUp()
        self.data_generator.repo()
        self.authorization = self.data_generator.authorization()
        self.login_as_superadmin()

    def test_get(self):
        """Tests GET requests."""
        doc = self.to_doc(self.client.get(
            '/haiti/admin/api_keys/list/', secure=True))
        self.assertTrue('Bob Vance' in doc.text)
        self.assertTrue('bob@fridge.com' in doc.text)
        self.assertTrue('Vance Refrigeration' in doc.text)
        # The first 10 elements with the "permissions" class are the
        # "Permissions" header and the individual permissions column headers.
        permissions_row = [el.text for el in doc.cssselect('.permission')[10:]]
        expected_permissions = [
            'fridge.com', 'x', 'x', 'x', None, None, None, None, 'x']
        self.assertEqual(permissions_row, expected_permissions)


class ApiKeyManagementViewTests(view_tests_base.ViewTestsBase):
    """Tests the API key management view."""

    def init_testbed_stubs(self):
        self.testbed.init_user_stub()
        self.testbed.init_datastore_v3_stub()

    def setUp(self):
        super(ApiKeyManagementViewTests, self).setUp()
        self.login_as_superadmin()

    def test_get_create_form(self):
        """Tests GET requests with no log key (i.e., the creation form)."""
        self.authorization = self.data_generator.authorization()
        res = self.client.get('/haiti/admin/api_keys/', secure=True)
        self.assertEqual(res.context['target_key'],
                         model.Authorization.DEFAULT_SETTINGS)
        self.assertEqual(res.context['operation_type'], 'create')

    def test_get_update_form(self):
        """Tests GET requests with a log key specified (i.e., an update form).
        """
        self.authorization = self.data_generator.authorization()
        management_log = model.ApiKeyManagementLog(
            repo='haiti',
            api_key=self.authorization.api_key,
            action=model.ApiKeyManagementLog.CREATE,
            ip_address='123.45.67.89',
            key_state=self.authorization.summary_str())
        management_log.put()
        res = self.client.get(
            '/haiti/admin/api_keys/',
            data={'log_key': management_log.key()},
            secure=True)
        self.assertEqual(res.context['target_key'].key(),
                         self.authorization.key())
        self.assertEqual(res.context['operation_type'], 'update')

    def test_post_render_update_form(self):
        """Tests POST requests to show the update form."""
        self.authorization = self.data_generator.authorization()
        params = {
            'edit_form': '1',
            'authorization_key': self.authorization.key(),
            'xsrf_token': self.xsrf_token('admin_api_keys'),
        }
        res = self.client.post(
            '/haiti/admin/api_keys/', data=params, secure=True)
        self.assertEqual(res.context['target_key'].key(),
                         self.authorization.key())
        self.assertEqual(res.context['operation_type'], 'update')

    def test_create_key(self):
        """Tests POST requests to create a new key."""
        params = {
            'contact_name': 'Creed Bratton',
            'contact_email': 'creed@aol.com',
            'organization_name': 'Creed Inc.',
            'read_permission': 'true',
            'search_permission': 'true',
            'is_valid': 'true',
            'xsrf_token': self.xsrf_token('admin_api_keys'),
        }
        res = self.client.post(
            '/haiti/admin/api_keys/', data=params, secure=True,
            REMOTE_ADDR='11.22.33.44')
        # Check that the Authorization entity was generated correctly.
        auths = model.Authorization.all().filter('repo =', 'haiti')
        self.assertEqual(auths.count(), 1)
        auth = auths[0]
        self.assertEqual(auth.contact_name, 'Creed Bratton')
        self.assertEqual(auth.contact_email, 'creed@aol.com')
        self.assertEqual(auth.organization_name, 'Creed Inc.')
        self.assertTrue(auth.read_permission)
        self.assertTrue(auth.search_permission)
        self.assertTrue(auth.is_valid)
        self.assertIsNone(auth.domain_write_permission)
        self.assertFalse(auth.full_read_permission)
        self.assertFalse(auth.subscribe_permission)
        self.assertFalse(auth.mark_notes_reviewed)
        self.assertFalse(auth.believed_dead_permission)
        self.assertFalse(auth.stats_permission)
        self.assertIsInstance(res, django.http.HttpResponseRedirect)
        # A management log entry should have been created.
        management_logs = model.ApiKeyManagementLog.all()
        self.assertEqual(1, management_logs.count())
        management_log = management_logs[0]
        self.assertEqual(management_log.repo, 'haiti')
        self.assertEqual(management_log.api_key, auth.api_key)
        self.assertEqual(
            management_log.action, model.ApiKeyManagementLog.CREATE)
        self.assertEqual(management_log.ip_address, '11.22.33.44')
        self.assertTrue('Creed' in management_log.key_state)
        # The user should be redirected to the form with the log key in a GET
        # parameter.
        self.assertEqual(
            res.url,
            'https://testserver/haiti/admin/api_keys?repo=haiti&log_key=%s' %
            management_log.key())

    def test_update_key(self):
        """Tests POST request to update an existing key."""
        self.authorization = self.data_generator.authorization()
        params = {
            'key': self.authorization.key(),
            'contact_name': 'Phyllis Vance',
            'contact_email': 'phyllis@fridge.com',
            'organization_name': 'Vance Refrigeration',
            'domain_write_permission': 'fridge.com',
            'read_permission': 'true',
            'full_read_permission': 'true',
            'search_permission': 'true',
            'subscribe_permission': 'true',
            'is_valid': 'true',
            'xsrf_token': self.xsrf_token('admin_api_keys'),
        }
        res = self.client.post(
            '/haiti/admin/api_keys/', data=params, secure=True,
            REMOTE_ADDR='11.22.33.44')
        # Check that the Authorization entity was updated correctly.
        auths = model.Authorization.all().filter('repo =', 'haiti')
        self.assertEqual(auths.count(), 1)
        auth = auths[0]
        self.assertEqual(auth.key(), self.authorization.key())
        # Check that changes were made.
        self.assertEqual(auth.contact_name, 'Phyllis Vance')
        self.assertEqual(auth.contact_email, 'phyllis@fridge.com')
        self.assertTrue(auth.subscribe_permission)
        # A management log entry should have been created.
        management_logs = model.ApiKeyManagementLog.all()
        self.assertEqual(1, management_logs.count())
        management_log = management_logs[0]
        self.assertEqual(management_log.repo, 'haiti')
        self.assertEqual(management_log.api_key, auth.api_key)
        self.assertEqual(
            management_log.action, model.ApiKeyManagementLog.UPDATE)
        self.assertEqual(management_log.ip_address, '11.22.33.44')
        self.assertTrue('Phyllis' in management_log.key_state)
        # The user should be redirected to the form with the log key in a GET
        # parameter.
        self.assertEqual(
            res.url,
            'https://testserver/haiti/admin/api_keys?repo=haiti&log_key=%s' %
            management_log.key())
