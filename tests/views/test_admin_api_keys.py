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

import model

import view_tests_base


class ApiKeyListViewTests(view_tests_base.ViewTestsBase):
    """Tests the admin API keys list view."""

    def setUp(self):
        super(ApiKeyListViewTests, self).setUp()
        model.Repo(key_name='haiti').put()
        model.Authorization.create(
            'haiti',
            'secret_key',
            contact_name='Bob Vance',
            contact_email='bob@fridge.com',
            organization_name='Vance Refrigeration',
            domain_write_permission='fridge.com',
            read_permission=True,
            full_read_permission=True,
            search_permission=True,
            subscribe_permission=False,
            mark_notes_reviewed=False,
            believed_dead_permission=False,
            stats_permission=False,
            is_valid=True).put()
        self.login(is_admin=True)

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
        self.assertEquals(permissions_row, expected_permissions)
