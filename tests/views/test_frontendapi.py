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

import datetime

import mock
import six

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
                'mapDefaultCenter': [123.45, 67.89],
                'mapDefaultZoom': 8,
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
                'mapDefaultCenter': [123.45, 67.89],
                'mapDefaultZoom': 8,
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
                'mapDefaultCenter': [123.45, 67.89],
                'mapDefaultZoom': 8,
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

    @mock.patch('photo.create_photo')
    def test_postabc(self, mock_create_photo):
        mock_create_photo.return_value = (
            model.Photo.create(
                'haiti', image_data='pretend this is image data'),
            'http://www.example.com/photo.jpg')
        with open('../tests/testdata/small_image.png') as image_file:
            resp = self.client.post(
                '/haiti/d/create',
                data={
                    'given_name': 'Matt',
                    'family_name': 'Matthews',
                    'own_info': 'yes',
                    'photo': image_file,
                },
                secure=True)
        persons = model.Person.all()
        self.assertEqual(persons.count(), 1)
        self.assertEqual(persons[0].given_name, 'Matt')
        self.assertEqual(resp.json(), {'personId': persons[0].record_id})
        create_photo_call_args = mock_create_photo.call_args[0]
        self.assertEqual(create_photo_call_args[0].height, 100)
        self.assertEqual(create_photo_call_args[1], 'haiti')


class FrontendApiPersonViewTests(view_tests_base.ViewTestsBase):

    def setUp(self):
        super(FrontendApiPersonViewTests, self).setUp()
        self.data_generator.repo()

    def test_get_with_person(self):
        person = self.data_generator.person(
            expiry_date=datetime.datetime(2090, 1, 10),
            full_name='John Smith',
            age='40-45',
            sex='male',
            description='description here')
        resp = self.client.get(
            '/haiti/d/person', data={'id': person.record_id}, secure=True)
        self.assertEqual(
            resp.json(),
            {
                six.u('name'): six.u('John Smith'),
                six.u('sex'): six.u('male'),
                six.u('age'): six.u('40-45'),
                six.u('author_email'): six.u('alice.smith@example.com'),
                six.u('author_name'): six.u('Alice Smith'),
                six.u('author_phone'): six.u('111-111-1111'),
                six.u('description'): six.u('description here'),
                six.u('home_city'): six.u('Toronto'),
                six.u('home_country'): six.u(''),
                six.u('home_state'): six.u('Ontario'),
                six.u('description'): six.u('description here'),
                six.u('profile_pages'): [],
                six.u('source_date'): six.u('2010-01-01T00:00:00Z'),
                six.u('source_name'): six.u('Example Organization'),
                six.u('notes'): [],
            })

    def test_get_with_person_with_note(self):
        person = self.data_generator.person(
            expiry_date=datetime.datetime(2090, 1, 10),
            full_name='John Smith',
            age='40-45',
            sex='male',
            description='description here')
        note = self.data_generator.note(
            person_id=person.record_id,
            entry_date=datetime.datetime(2950, 1, 1),
            source_date=datetime.datetime(2950, 1, 2),
            author_name='Fred',
            text='text here')
        resp = self.client.get(
            '/haiti/d/person', data={'id': person.record_id}, secure=True)
        note_list = resp.json()['notes']
        self.assertEqual(len(note_list), 1)
        self.assertEqual(
            note_list[0],
            {
                six.u('note_record_id'): note.record_id,
                six.u('source_date'): six.u('2950-01-02T00:00:00Z'),
                six.u('author_name'): six.u('Fred'),
                six.u('author_made_contact'): False,
                six.u('status'): six.u('believed_missing'),
                six.u('text'): six.u('text here'),
            })

    def test_get_with_nonexistent_person(self):
        resp = self.client.get(
            '/haiti/d/person', data={'id': 'nonexistent.record'}, secure=True)
        self.assertEqual(resp.status_code, 404)

    def test_get_with_expired_person(self):
        person = self.data_generator.person()
        resp = self.client.get(
            '/haiti/d/person', data={'id': person.record_id}, secure=True)
        self.assertEqual(resp.status_code, 404)

    def test_get_with_deactivated_repo(self):
        self.data_generator.repo(
            repo_id='malaysia',
            activation_status=model.Repo.ActivationStatus.DEACTIVATED)
        person = self.data_generator.person(
            repo_id='malaysia',
            expiry_date=datetime.datetime(2090, 1, 10))
        resp = self.client.get(
            '/haiti/d/person', data={'id': person.record_id}, secure=True)
        self.assertEqual(resp.status_code, 404)


class FrontendApiAddNoteViewTests(view_tests_base.ViewTestsBase):

    def setUp(self):
        super(FrontendApiAddNoteViewTests, self).setUp()
        self.data_generator.repo()
        self.person = self.data_generator.person()

    def test_add_note(self):
        self.client.post(
            '/haiti/d/add_note',
            data={
                'id': self.person.record_id,
                'author_name': 'Adam',
                'text': 'Here is some text.',
            },
            secure=True)
        notes = model.Person.get('haiti', self.person.record_id).get_notes()
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].author_name, 'Adam')
