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


from google.appengine.ext import db

import model

import view_tests_base


class AdminDashboardViewTests(view_tests_base.ViewTestsBase):

    def setUp(self):
        super(AdminDashboardViewTests, self).setUp()
        self.data_generator.repo()
        self.data_generator.repo('pakistan')
        self.login_as_manager()

    def test_get(self):
        db.put([
            model.Counter(
                scan_name='Person', repo='haiti', last_key='', count_all=278),
            model.Counter(
                scan_name='Person', repo='pakistan', last_key='',
                count_all=127),
            model.Counter(
                scan_name='Note', repo='haiti', last_key='', count_all=12),
            model.Counter(
                scan_name='Note', repo='pakistan', last_key='', count_all=8)
        ])
        resp = self.client.get('/global/admin/dashboard')
        self.assertEqual(resp.status_code, 200)
