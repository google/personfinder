#!/usr/bin/python2.7
# encoding: utf-8
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

"""Test cases for end-to-end testing.  Run with the server_tests script."""



from google.appengine.api import images
from photo import MAX_IMAGE_DIMENSION
from server_tests_base import ServerTestsBase


class PhotoTests(ServerTestsBase):
    """Tests that verify photo upload and serving."""
    def submit_create(self, **kwargs):
        doc = self.go('/haiti/create?role=provide')
        form = doc.cssselect_one('form')
        return self.s.submit(form,
                             given_name='_test_given_name',
                             family_name='_test_family_name',
                             author_name='_test_author_name',
                             text='_test_text',
                             **kwargs)

    def test_upload_photo(self):
        """Verifies a photo is uploaded and properly served on the server."""
        # Create a new person record with a profile photo.
        photo = file('tests/testdata/small_image.png')
        original_image = images.Image(photo.read())
        doc = self.submit_create(photo=photo)
        # Verify the image is uploaded and displayed on the view page.
        photo = doc.cssselect_one('img.photo')
        photo_anchor = doc.xpath_one('//a[img[@class="photo"]]')
        # Verify the image is served properly by checking the image metadata.
        doc = self.s.go(photo.get('src'))
        image = images.Image(doc.content_bytes)
        assert image.format == images.PNG
        assert image.width == original_image.width
        assert image.height == original_image.height
        # Follow the link on the image and verify the same image is served.
        doc = self.s.follow(photo_anchor)
        image = images.Image(doc.content_bytes)
        assert image.format == images.PNG
        assert image.width == original_image.width
        assert image.height == original_image.height

    def test_upload_photos_with_transformation(self):
        """Uploads both profile photo and note photo and verifies the images are
        properly transformed and served on the server i.e., jpg is converted to
        png and a large image is resized to match MAX_IMAGE_DIMENSION."""
        # Create a new person record with a profile photo and a note photo.
        photo = file('tests/testdata/small_image.jpg')
        note_photo = file('tests/testdata/large_image.png')
        original_image = images.Image(photo.read())
        doc = self.submit_create(photo=photo, note_photo=note_photo)
        # Verify the images are uploaded and displayed on the view page.
        photos = doc.cssselect('img.photo')
        assert len(photos) == 2
        # Verify the profile image is converted to png.
        doc = self.s.go(photos[0].get('src'))
        image = images.Image(doc.content_bytes)
        assert image.format == images.PNG
        assert image.width == original_image.width
        assert image.height == original_image.height
        # Verify the note image is resized to match MAX_IMAGE_DIMENSION.
        doc = self.s.go(photos[1].get('src'))
        image = images.Image(doc.content_bytes)
        assert image.format == images.PNG
        assert image.width == MAX_IMAGE_DIMENSION
        assert image.height == MAX_IMAGE_DIMENSION

    def test_upload_empty_photo(self):
        """Uploads an empty image and verifies no img tag in the view page."""
        # Create a new person record with a zero-byte profile photo.
        photo = file('tests/testdata/empty_image.png')
        doc = self.submit_create(photo=photo)
        # Verify there is no img tag in the view page.
        assert '_test_given_name' in doc.text
        assert not doc.cssselect('img.photo')

    def test_upload_broken_photo(self):
        """Uploads a broken image and verifies an error message is displayed."""
        # Create a new person record with a broken profile photo.
        photo = file('tests/testdata/broken_image.png')
        doc = self.submit_create(photo=photo)
        # Verify an error message is displayed.
        assert not doc.cssselect('img.photo')
        assert 'unrecognized format' in doc.text

