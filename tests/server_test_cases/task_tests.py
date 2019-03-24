import datetime
import mock
import os

from google.appengine.api import images
from google.appengine.ext import testbed

import model
from server_tests_base import ServerTestsBase
import tasks
import test_handler


class ApiPersonPostProcessorTests(ServerTestsBase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.testbed.init_datastore_v3_stub()
        # root_path must be set the the location of queue.yaml.
        # Otherwise, only the 'default' queue will be available.
        path_to_app = os.path.join(os.path.dirname(__file__), '../../app')
        self.testbed.init_taskqueue_stub(root_path=path_to_app)
        self.taskqueue_stub = self.testbed.get_stub(
            testbed.TASKQUEUE_SERVICE_NAME)
        model.Repo(key_name='haiti').put()
        self.handler = test_handler.initialize_handler(
            handler_class=tasks.ApiPersonPostProcessor,
            action=tasks.ApiPersonPostProcessor.ACTION,
            repo='haiti', environ=None, params={'id': 'haiti/0325'})

    def tearDown(self):
        self.testbed.deactivate()

    def test_store_photo(self):
        photo_url = 'http://www.example.com/photo.jpg'
        photo_response = mock.MagicMock()
        photo_response.content = open('tests/testdata/tiny_image.png').read()
        person = model.Person.create_original_with_record_id(
            'haiti',
            'haiti/0325',
            given_name='Yayoi',
            family_name='Takatsuki',
            full_name='Yayoi Takatsuki',
            entry_date=datetime.datetime(2010, 1, 1, 0, 0, 0),
            photo_url=photo_url
        )
        person.put()
        with mock.patch('requests.get') as mock_requests_get:
            mock_requests_get.return_value = photo_response
            self.handler.get()
            mock_requests_get.assert_called_once_with(photo_url)
            person = model.Person.get('haiti', 'haiti/0325')
            assert person.photo is not None
            assert images.Image(person.photo.image_data).height == 40

    def test_no_person_record(self):
        self.handler.get()
        tasks = self.taskqueue_stub.get_filtered_tasks()
        self.assertEqual(len(tasks), 1)
        assert tasks[0].url == ('/haiti/tasks/api_person_post_processor?'
                                'id=haiti%2F0325')


class ApiNotePostProcessorTests(ServerTestsBase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.testbed.init_datastore_v3_stub()
        # root_path must be set the the location of queue.yaml.
        # Otherwise, only the 'default' queue will be available.
        path_to_app = os.path.join(os.path.dirname(__file__), '../../app')
        self.testbed.init_taskqueue_stub(root_path=path_to_app)
        self.taskqueue_stub = self.testbed.get_stub(
            testbed.TASKQUEUE_SERVICE_NAME)
        model.Repo(key_name='haiti').put()
        self.handler = test_handler.initialize_handler(
            handler_class=tasks.ApiNotePostProcessor,
            action=tasks.ApiNotePostProcessor.ACTION,
            repo='haiti', environ=None, params={'id': 'haiti/note.0325'})

    def tearDown(self):
        self.testbed.deactivate()

    def test_store_photo(self):
        photo_url = 'http://www.example.com/photo.jpg'
        photo_response = mock.MagicMock()
        photo_response.content = open('tests/testdata/tiny_image.png').read()
        note = model.Note.create_original_with_record_id(
            'haiti',
            'haiti/note.0325',
            person_record_id='haiti/0325',
            status=u'believed_missing',
            author_email='note1.author@example.com',
            author_made_contact=False,
            photo_url='http://www.example.com/photo.jpg',
            entry_date=datetime.datetime(2010, 1, 2),
            source_date=datetime.datetime(2010, 1, 1))
        note.put()
        with mock.patch('requests.get') as mock_requests_get:
            mock_requests_get.return_value = photo_response
            self.handler.get()
            mock_requests_get.assert_called_once_with(photo_url)
            note = model.Note.get('haiti', 'haiti/note.0325')
            assert note.photo is not None
            assert images.Image(note.photo.image_data).height == 40

    def test_no_note_record(self):
        self.handler.get()
        tasks = self.taskqueue_stub.get_filtered_tasks()
        self.assertEqual(len(tasks), 1)
        assert tasks[0].url == ('/haiti/tasks/api_note_post_processor?'
                                'id=haiti%2Fnote.0325')
