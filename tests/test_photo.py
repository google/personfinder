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
import test_handler

class PhotoTests(unittest.TestCase):
    def test_get_photo_url(self):
        entity = model.Photo.create('haiti', image_data='xyz')
        entity.put()
        id = entity.key().name().split(':')[1]

        os.environ['HTTP_HOST'] = 'example.appspot.com'
        ph = test_handler.initialize_handler(
            photo.Handler, 'photo', environ=os.environ)
        self.assertEquals(
            'http://example.appspot.com/haiti/photo?id=%s' % id,
            photo.get_photo_url(entity, ph))


if __name__ == '__main__':
    unittest.main()
