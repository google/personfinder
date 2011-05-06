# Copyright 2010 Google Inc.
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

"""Tests for photo.py."""

__author__ = 'kpy@google.com (Ka-Ping Yee)'

import os
import unittest

import model
import photo


class PhotoTests(unittest.TestCase):
    def test_get_photo_url(self):
        entity = model.Photo()
        entity.put()
        id = entity.key().id()

        # Check that the photo URL is correct for a regular app.
        os.environ['SERVER_PORT'] = '80'
        os.environ['APPLICATION_ID'] = 'example'
        os.environ['HTTP_HOST'] = 'example.appspot.com'
        assert photo.get_photo_url(entity) == \
            'https://example.appspot.com/photo?id=%s' % id

        # Check that the photo URL is correct for a high-replication app.
        os.environ['SERVER_PORT'] = '80'
        os.environ['APPLICATION_ID'] = 's~hr-example'
        os.environ['HTTP_HOST'] = 'hr-example.appspot.com'
        assert photo.get_photo_url(entity) == \
            'https://hr-example.appspot.com/photo?id=%s' % id

        # Check that the photo URL is correct for a development server.
        os.environ['SERVER_PORT'] = '8000'
        os.environ['APPLICATION_ID'] = 'example'
        os.environ['HTTP_HOST'] = 'localhost:8000'
        assert photo.get_photo_url(entity) == \
            'http://localhost:8000/photo?id=%s' % id


if __name__ == '__main__':
    unittest.main()
