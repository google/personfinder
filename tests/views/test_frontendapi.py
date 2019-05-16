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


"""Tests for the frontend API."""

import view_tests_base


class FrontendApiResultsViewTests(view_tests_base.ViewTestsBase):
    """Tests the frontend API's results view."""

    def setUp(self):
        super(FrontendApiResultsViewTests, self).setUp()
        self.data_generator.repo()

    def test_get_no_results(self):
        """Tests GET requests with no expected results."""
        resp = self.client.get('/haiti/d/results?query_name=fred', secure=True)
        self.assertEqual(resp.json(), [])

    def test_get_with_results(self):
        """Tests GET requests with expected results."""
        john1 = self.data_generator.person_a(
            index=True, full_name='John Smith', alternate_names='Johnny',
            photo_url='http://testserver/haiti/photo/1')
        john2 = self.data_generator.person(
            index=True, given_name='John', family_name='Schiff',
            full_name='John Schiff',
            photo_url='http://www.example.com/photo.jpg')
        self.data_generator.person_b(index=True)  # Not named John.
        resp = self.client.get('/haiti/d/results?query_name=john', secure=True)
        sorted_json = sorted(resp.json(), key=lambda p: p['personId'])
        self.assertEqual(
            sorted_json,
            [
                {
                    'personId': john1.record_id,
                    'fullNames': ['John Smith'],
                    'alternateNames': ['Johnny'],
                    'timestamp': '2010-01-01T00:00:00',
                    'timestampType': 'creation',
                    'localPhotoUrl':
                    'http://testserver/haiti/photo/1?thumb=true',
                },
                {
                    'personId': john2.record_id,
                    'fullNames': ['John Schiff'],
                    'alternateNames': [],
                    'timestamp': '2010-01-01T00:00:00',
                    'timestampType': 'creation',
                    'localPhotoUrl': None,
                },
            ])
