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
"""Tests for the sitemap ping task."""

import mock

# pylint: disable=wrong-import-order
# pylint sometimes thinks config is a standard import that belongs before the
# django import. It's mistaken; config is our own module (if you run
# python -c "import config", it produces an error saying config doesn't exist).
# Filed issue #626 to move us out of the global namespace someday, which would
# prevent stuff like this.
import config

import task_tests_base


class SitemapPingTests(task_tests_base.TaskTestsBase):
    """Tests the sitemap ping task."""

    def test_get(self):
        """Tests GET requests."""
        # We set it to "really" ping index servers for the test. Since we're
        # also mocking out requests.get though, it won't really succeed in
        # pinging anything.
        config.set(ping_sitemap_indexers=True)
        with mock.patch('requests.get') as requests_mock:
            self.run_task(
                '/global/tasks/sitemap_ping', {'search_engine': 'google'})
            self.assertEqual(len(requests_mock.call_args_list), 1)
            call_args, _ = requests_mock.call_args_list[0]
            self.assertEqual(call_args[0],
                             ('https://www.google.com/ping?sitemap='
                              'https%3A//testserver/global/sitemap'))
