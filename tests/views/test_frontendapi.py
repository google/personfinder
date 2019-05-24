# encoding: utf-8
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

import model

import view_tests_base


class FrontendApiRepoViewTests(view_tests_base.ViewTestsBase):
    """Tests the frontend API's repo view."""

    def test_repo(self):
        self.data_generator.repo(repo_id='haiti')
        self.data_generator.setup_repo_config(repo_id='haiti')
        resp = self.client.get('/haiti/d/repo', secure=True)
        self.assertEqual(
            {
                'repoId': 'haiti',
                'title': 'Haiti',
                'recordCount': 0,
            },
            resp.json())

    def test_nonexistent_repo(self):
        resp = self.client.get('/estonia/d/repo?lang=es', secure=True)
        self.assertEqual(resp.status_code, 404)

    def test_deactivated_repo(self):
        self.data_generator.repo(
            repo_id='haiti',
            activation_status=model.Repo.ActivationStatus.DEACTIVATED)
        resp = self.client.get('/haiti/d/repo', secure=True)
        self.assertEqual(resp.status_code, 404)

    def test_repo_with_count(self):
        self.data_generator.repo(repo_id='haiti')
        self.data_generator.setup_repo_config(repo_id='haiti')
        counter = model.Counter(repo='haiti', scan_name='person')
        counter.count_all = 180
        counter.put()
        resp = self.client.get('/haiti/d/repo', secure=True)
        self.assertEqual(
            {
                'repoId': 'haiti',
                'title': 'Haiti',
                'recordCount': 200,
            },
            resp.json())

    def test_repo_other_language(self):
        self.data_generator.repo(repo_id='latvia')
        self.data_generator.setup_repo_config(
            repo_id='latvia',
            language_menu_options=['lv', 'es'],
            repo_titles={'lv': 'Latvija', 'es': 'Letonia'})
        resp = self.client.get('/latvia/d/repo?lang=es', secure=True)
        self.assertEqual(
            {
                'repoId': 'latvia',
                'title': 'Letonia',
                'recordCount': 0,
            },
            resp.json())

    def test_global_no_repos(self):
        resp = self.client.get('/global/d/repo', secure=True)
        self.assertEqual(resp.json(), [])

    def test_global_one_repo(self):
        self.data_generator.repo(repo_id='haiti')
        self.data_generator.setup_repo_config(repo_id='haiti')
        resp = self.client.get('/global/d/repo', secure=True)
        self.assertEqual(
            [
                {
                    'repoId': 'haiti',
                    'title': 'Haiti',
                    'recordCount': 0,
                },
            ],
            resp.json())

    def test_global_multiple_repos(self):
        self.data_generator.repo(repo_id='haiti')
        self.data_generator.setup_repo_config(repo_id='haiti')
        self.data_generator.repo(repo_id='japan')
        self.data_generator.setup_repo_config(
            repo_id='japan',
            language_menu_options=['ja', 'en'],
            repo_titles={'ja': '日本', 'en': 'Japan'})
        resp = self.client.get('/global/d/repo', secure=True)
        self.assertEqual(
            [
                {
                    'repoId': 'haiti',
                    'title': 'Haiti',
                    'recordCount': 0,
                },
                {
                    'repoId': 'japan',
                    'title': 'Japan',
                    'recordCount': 0,
                },
            ],
            resp.json())


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
                    'timestamp': '2010-01-01T00:00:00Z',
                    'timestampType': 'creation',
                    'localPhotoUrl':
                    'http://testserver/haiti/photo/1?thumb=true',
                },
                {
                    'personId': john2.record_id,
                    'fullNames': ['John Schiff'],
                    'alternateNames': [],
                    'timestamp': '2010-01-01T00:00:00Z',
                    'timestampType': 'creation',
                    'localPhotoUrl': None,
                },
            ])


class FrontendApiCreateViewTests(view_tests_base.ViewTestsBase):

    def setUp(self):
        super(FrontendApiCreateViewTests, self).setUp()
        self.data_generator.repo()

    def test_post(self):
        self.client.post(
            '/haiti/d/create',
            data={
                'given_name': 'Matt',
                'family_name': 'Matthews',
                'own_info': 'yes',
            },
            secure=True)
        persons = model.Person.all()
        self.assertEqual(persons.count(), 1)
        self.assertEqual(persons[0].given_name, 'Matt')
