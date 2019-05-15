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


import django

import view_tests_base


class AdminBaseViewTests(view_tests_base.ViewTestsBase):

    def test_redirect_non_logged_in(self):
        """Tests that users who aren't logged in are redirected."""
        self.testbed.setup_env(
            user_email='',
            user_id='',
            user_is_admin='0',
            overwrite=True)
        # This tests functionality in the admin base class; it shouldn't really
        # matter which page we hit to test it.
        resp = self.client.get('/global/admin')
        self.assertIsInstance(resp, django.http.HttpResponseRedirect)
