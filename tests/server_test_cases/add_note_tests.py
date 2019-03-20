import mock
import unittest

from google.appengine.ext import testbed

import add_note
from server_tests_base import ServerTestsBase
import test_handler


class AddNoteTests(ServerTestsBase):

    def test_upload_photo(self):
        person, note = self.setup_person_and_note()
        photo_url = 'http://www.example.com/photo.jpg'
        photo_response = mock.MagicMock()
        photo_response.content = open('tests/testdata/tiny_image.png').read()
        params = {
            'text': 'here is some text',
            'author_name': 'Max',
            'author_email': 'max@example.com',
            'id': person.key().name().split(':')[1],
            'note_photo_url': photo_url,
        }
        handler = test_handler.initialize_handler(
            add_note.Handler, 'add_note', params=params)
        with mock.patch('requests.get') as mock_requests_get:
            mock_requests_get.return_value = photo_response
            handler.post()
            # make sure create.py's create_photo_from_input was called
            mock_requests_get.assert_called_once_with(photo_url)


if __name__ == '__main__':
    unittest.main()
