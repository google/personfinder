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


"""Tests for the sitemap."""

import re

import model

import view_tests_base


class SitemapViewTests(view_tests_base.ViewTestsBase):
    """Tests the sitemap view."""

    _REPO_URL_MATCHER = re.compile(r'https://testserver/(.+)\?lang=(.+)')

    def setUp(self):
        super(SitemapViewTests, self).setUp()
        self.data_generator.repo(repo_id='haiti')
        self.data_generator.repo(repo_id='japan')
        # The unlaunched repo shouldn't appear in the sitemap.
        self.data_generator.repo(
            repo_id='minnesota',
            activation_status=model.Repo.ActivationStatus.STAGING)

    def test_get(self):
        """Tests GET requests."""
        res = self.client.get('/global/sitemap/', secure=True)
        urimaps = res.context['urimaps']
        # There should be three URLs (the global homepage and the two active
        # repos).
        self.assertEqual(len(urimaps), 3)
        # The first one should be the global homepage.
        self.assertEqual(urimaps[0]['en'], 'https://testserver/?lang=en')
        # Check a couple arbitrary languages for the repo URLs.
        uri1_match = SitemapViewTests._REPO_URL_MATCHER.match(urimaps[1]['km'])
        self.assertIsNotNone(uri1_match)
        uri2_match = SitemapViewTests._REPO_URL_MATCHER.match(urimaps[2]['pl'])
        self.assertIsNotNone(uri2_match)
        # The repo URLs aren't in any particular order in the sitemap, so sort
        # the results ourselves for comparison.
        self.assertEqual(sorted([uri1_match.group(1), uri2_match.group(1)]),
                         ['haiti', 'japan'])
        self.assertEqual(uri1_match.group(2), 'km')
        self.assertEqual(uri2_match.group(2), 'pl')
