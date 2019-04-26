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
"""Tests for the admin ACLs page."""

import datetime

import django
import django.http
import django.test

import config
import model
import modelmodule.admin_acls as admin_acls_model
import utils

import view_tests_base


class AdminAclsViewTests(view_tests_base.ViewTestsBase):
    """Tests the admin ACLs view."""

    def setUp(self):
        super(AdminAclsViewTests, self).setUp()
        self.data_generator.repo()
        self.login(is_admin=True)

    def test_get_with_no_existing_users(self):
        """Tests GET requests when there's no users with permissions yet."""
        res = self.client.get('/haiti/admin/acls/', secure=True)
        self.assertEqual(res.context['existing_acls'].count(), 0)

    def test_get_with_existing_users(self):
        """Tests GET requests when there are users with permissions."""
        self.data_generator.admin_permission()
        self.data_generator.admin_permission(email_address='m@mib.gov')
        res = self.client.get('/haiti/admin/acls/', secure=True)
        self.assertEqual(res.context['existing_acls'].count(), 2)

    def test_get_default_expiration_date(self):
        """Tests that the expected default expiration date is correctly."""
        utils.set_utcnow_for_test(datetime.datetime(2010, 1, 5))
        res = self.client.get('/haiti/admin/acls/', secure=True)
        self.assertEqual(
            res.context['default_expiration_date'],
            datetime.datetime(2011, 1, 5))

    def test_add_moderator(self):
        """Tests adding a moderator."""
        get_doc = self.to_doc(self.client.get(
            '/haiti/admin/acls/', secure=True))
        xsrf_token = get_doc.cssselect_one('input[name="xsrf_token"]').get(
            'value')
        post_resp = self.client.post('/haiti/admin/acls', {
            'xsrf_token': xsrf_token,
            'email_address': 'l@mib.gov',
            'expiration_date': '2019-04-25',
            'level': 'moderator',
        }, secure=True)
        acls = admin_acls_model.AdminPermission.all()
        self.assertEqual(acls.count(), 1)
        acl = acls[0]
        self.assertEqual(acl.email_address, 'l@mib.gov')
        self.assertEqual(acl.expiration_date, datetime.datetime(2019, 4, 25))
        self.assertEqual(
            acl.access_level,
            admin_acls_model.AdminPermission.AccessLevel.MODERATOR)
        res = self.client.get('/haiti/admin/acls/', secure=True)
        self.assertEqual(
            res.context['existing_acls'][0].email_address, 'l@mib.gov')

    def test_add_manager(self):
        """Tests adding a manager."""
        get_doc = self.to_doc(self.client.get(
            '/haiti/admin/acls/', secure=True))
        xsrf_token = get_doc.cssselect_one('input[name="xsrf_token"]').get(
            'value')
        post_resp = self.client.post('/haiti/admin/acls', {
            'xsrf_token': xsrf_token,
            'email_address': 'l@mib.gov',
            'expiration_date': '2019-04-25',
            'level': 'manager',
        }, secure=True)
        acls = admin_acls_model.AdminPermission.all()
        self.assertEqual(acls.count(), 1)
        acl = acls[0]
        self.assertEqual(acl.email_address, 'l@mib.gov')
        self.assertEqual(acl.expiration_date, datetime.datetime(2019, 4, 25))
        self.assertEqual(
            acl.access_level,
            admin_acls_model.AdminPermission.AccessLevel.MANAGER)
        res = self.client.get('/haiti/admin/acls/', secure=True)
        self.assertEqual(
            res.context['existing_acls'][0].email_address, 'l@mib.gov')

    def test_add_superadmin(self):
        """Tests adding a superadmin."""
        get_doc = self.to_doc(self.client.get(
            '/haiti/admin/acls/', secure=True))
        xsrf_token = get_doc.cssselect_one('input[name="xsrf_token"]').get(
            'value')
        post_resp = self.client.post('/haiti/admin/acls', {
            'xsrf_token': xsrf_token,
            'email_address': 'l@mib.gov',
            'expiration_date': '2019-04-25',
            'level': 'superadmin',
        }, secure=True)
        acls = admin_acls_model.AdminPermission.all()
        self.assertEqual(acls.count(), 1)
        acl = acls[0]
        self.assertEqual(acl.email_address, 'l@mib.gov')
        self.assertEqual(acl.expiration_date, datetime.datetime(2019, 4, 25))
        self.assertEqual(
            acl.access_level,
            admin_acls_model.AdminPermission.AccessLevel.SUPERADMIN)
        res = self.client.get('/haiti/admin/acls/', secure=True)
        self.assertEqual(
            res.context['existing_acls'][0].email_address, 'l@mib.gov')

    def test_edit_access_level(self):
        """Tests editing the access level for a user."""
        self.data_generator.admin_permission(
            email_address='j@mib.gov',
            expiration_date=datetime.datetime(2019, 4, 25),
            access_level=admin_acls_model.AdminPermission.AccessLevel.MODERATOR)
        get_doc = self.to_doc(self.client.get(
            '/haiti/admin/acls/', secure=True))
        xsrf_token = get_doc.cssselect('input[name="xsrf_token"]')[1].get(
            'value')
        post_resp = self.client.post('/haiti/admin/acls', {
            'xsrf_token': xsrf_token,
            'email_address': 'j@mib.gov',
            'expiration_date': '2019-04-25',
            'level': 'superadmin',
        }, secure=True)
        acls = admin_acls_model.AdminPermission.all()
        self.assertEqual(acls.count(), 1)
        acl = acls[0]
        self.assertEqual(acl.email_address, 'j@mib.gov')
        self.assertEqual(acl.expiration_date, datetime.datetime(2019, 4, 25))
        self.assertEqual(
            acl.access_level,
            admin_acls_model.AdminPermission.AccessLevel.SUPERADMIN)

    def test_edit_expiration_date(self):
        """Tests editing the expiration date for a permission."""
        self.data_generator.admin_permission(
            email_address='j@mib.gov',
            expiration_date=datetime.datetime(2019, 4, 25),
            access_level=admin_acls_model.AdminPermission.AccessLevel.MODERATOR)
        get_doc = self.to_doc(self.client.get(
            '/haiti/admin/acls/', secure=True))
        xsrf_token = get_doc.cssselect('input[name="xsrf_token"]')[1].get(
            'value')
        post_resp = self.client.post('/haiti/admin/acls', {
            'xsrf_token': xsrf_token,
            'email_address': 'j@mib.gov',
            'expiration_date': '2019-05-25',
            'level': 'moderator',
        }, secure=True)
        acls = admin_acls_model.AdminPermission.all()
        self.assertEqual(acls.count(), 1)
        acl = acls[0]
        self.assertEqual(acl.email_address, 'j@mib.gov')
        self.assertEqual(acl.expiration_date, datetime.datetime(2019, 5, 25))
        self.assertEqual(
            acl.access_level,
            admin_acls_model.AdminPermission.AccessLevel.MODERATOR)

    def test_revoke_access(self):
        """Tests revoking admin access."""
        self.data_generator.admin_permission(email_address='j@mib.gov')
        get_doc = self.to_doc(self.client.get(
            '/haiti/admin/acls/', secure=True))
        xsrf_token = get_doc.cssselect('input[name="xsrf_token"]')[1].get(
            'value')
        post_resp = self.client.post('/haiti/admin/acls', {
            'xsrf_token': xsrf_token,
            'email_address': 'j@mib.gov',
            'expiration_date': '2019-04-25',
            'level': 'moderator',
            'revoke_button': 'Revoke',
        }, secure=True)
        acls = admin_acls_model.AdminPermission.all()
        self.assertEqual(acls.count(), 0)
