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


"""Tests for the admin delete-record page."""

import django
import django.http
import django.test
import six.moves.urllib.parse as urlparse

import const

import view_tests_base


class AdminDeleteRecordViewTests(view_tests_base.ViewTestsBase):
    """Tests the admin delete-record view."""

    def setUp(self):
        super(AdminDeleteRecordViewTests, self).setUp()
        self.login_as_moderator()
        self.data_generator.repo()
        self.person = self.data_generator.person()

    def test_get(self):
        """Tests GET requests."""
        res = self.client.get('/global/admin/delete_record/', secure=True)
        self.assertEqual(res.context['id'], '%s/person.' % const.HOME_DOMAIN)

    def test_post(self):
        """Tests POST requests to delete a record."""
        get_doc = self.to_doc(self.client.get(
            '/global/admin/delete_record/', secure=True))
        xsrf_token = get_doc.cssselect_one('input[name="xsrf_token"]').get(
            'value')
        post_resp = self.client.post('/haiti/admin/delete_record/', {
            'xsrf_token': xsrf_token,
            'id': self.person.record_id,
        }, secure=True)
        # Check that the user's redirected to the repo's main admin page.
        self.assertIsInstance(post_resp, django.http.HttpResponseRedirect)
        parse = urlparse.urlparse(post_resp.url)
        self.assertEqual('/haiti/delete', parse.path)
        query_params = dict(urlparse.parse_qsl(parse.query))
        self.assertEqual(query_params['id'], self.person.record_id)
        # Check that the signature param is present and not the empty string.
        self.assertTrue(len(query_params['signature']) > 1)
