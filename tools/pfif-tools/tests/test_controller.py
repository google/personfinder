#!/usr/bin/env python
# coding=utf-8
# Copyright 2011 Google Inc.
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

"""Tests for validator_controller.py"""

import copy
import os
from StringIO import StringIO
import unittest
import utils

import django
from django.test import Client
from django.test.utils import setup_test_environment, teardown_test_environment

import controller
import settings
import tests.pfif_xml as PfifXml

class ControllerTests(unittest.TestCase):
  """Tests for the controller."""

  def setUp(self):
    # TODO(nworden): see if there's a way to avoid this. You'd think
    # settings.BASE_DIR would be useful here but I can't figure out how to make
    # it work for prod, local servers, and tests without overriding the value in
    # tests.
    # The Django test client doesn't actually run a whole server, which is
    # really nice because it's much faster, but it does seem to mess with the
    # template loader, I guess because it's not running from where it normally
    # would (in the app directory).
    settings.TEMPLATES[0]['DIRS'] = ['app/resources']
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
    django.setup()
    setup_test_environment()
    self.client = Client()

  def tearDown(self):
    teardown_test_environment()

  def make_request(
      self, post_data, path='/validate/results'):
    """Makes a request for the validator with content as the HTTP POST content.
    Returns the response."""
    return self.client.post(path, copy.deepcopy(post_data))

  # file tests

  def test_no_xml_fails_gracefully(self):
    """If the user tries to validate with no input, there should not be an
    exception."""
    for path in ['/validate/results', '/diff/results']:
      response = self.make_request({}, path=path)
      self.assertTrue("html" in response.content)

  def test_pasting_xml(self):
    """The page should have the correct number of errors in the header when
    using the pfif_xml_1 POST variable to send PFIF XML."""
    response = self.make_request(
        {'pfif_xml_1' : PfifXml.XML_TWO_DUPLICATE_NO_CHILD})
    self.assertTrue("3 Messages" in response.content)

  def test_file_upload(self):
    """The page should have the correct number of errors in the header when
    using the pfif_xml_file_1 POST variable to send PFIF XML."""
    xml_file = StringIO(PfifXml.XML_TWO_DUPLICATE_NO_CHILD)
    xml_file.name = 'two_duplicate_no_child.xml'
    response = self.make_request({'pfif_xml_file_1': xml_file})
    self.assertTrue("3 Messages" in response.content)

  def test_url_upload(self):
    """The page should have the correct number of errors in the header when
    using the pfif_xml_url_1 POST variable to send PFIF XML."""
    utils.set_file_for_test(StringIO(PfifXml.XML_TWO_DUPLICATE_NO_CHILD))
    response = self.make_request({'pfif_xml_url_1' : 'dummy_url'})
    self.assertTrue("3 Messages" in response.content)

  # validator

  def test_validator_options(self):
    """The validator results page should have a span or div for each print
    option."""
    xml_file = StringIO(PfifXml.XML_EXPIRE_99_EMPTY_DATA)
    xml_file.name = 'xml_expire_99_empty_data.xml'
    post_dict = {'pfif_xml_file_1' : xml_file,
                 'print_options': ['show_errors']}
    response = self.make_request(post_dict)
    self.assertTrue('ERROR' in response.content)
    self.assertTrue('message_type' in response.content)
    self.assertTrue('message_category' in response.content)

    post_dict['print_options'].append('show_warnings')
    response = self.make_request(post_dict)
    self.assertTrue('WARNING' in response.content)

    post_dict['print_options'].append('show_line_numbers')
    response = self.make_request(post_dict)
    self.assertTrue('message_line_number' in response.content)

    post_dict['print_options'].append('show_record_ids')
    response = self.make_request(post_dict)
    self.assertTrue('record_id' in response.content)

    post_dict['print_options'].append('show_full_line')
    response = self.make_request(post_dict)
    self.assertTrue('message_xml_full_line' in response.content)

    # EXPIRE_99 doesn't have any errors with xml element text or tag, so we use
    # a different XML file
    xml_file = StringIO(PfifXml.XML_INCORRECT_FORMAT_11)
    xml_file.name = 'xml_incorrect_format_11.xml'
    post_dict['pfif_xml_file_1'] = xml_file
    post_dict['print_options'].append('show_xml_tag')
    response = self.make_request(post_dict)
    self.assertTrue('message_xml_tag' in response.content)

    post_dict['print_options'].append('show_xml_text')
    response = self.make_request(post_dict)
    self.assertTrue('message_xml_text' in response.content)

  # diff

  def test_diff(self):
    """The diff results page should have a header and a div for each message."""
    xml_file = StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_1)
    xml_file.name = 'added_deleted_changed_1.xml'
    utils.set_file_for_test(StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_2))
    post_dict = {
        'pfif_xml_file_1' : xml_file, 'pfif_xml_url_2' : 'fake_url',
        'options' : ['text_is_case_sensitive']}
    response = self.make_request(post_dict, path='/diff/results')
    response_str = response.content

    # set the test file again because the first one will be at the end, and the
    # xml parser doesn't have to seek(0) on it.
    utils.set_file_for_test(StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_2))
    post_dict['options'].append('group_messages_by_record')
    grouped_response = self.make_request(post_dict, path='/diff/results')
    grouped_response_str = grouped_response.content

    # The header should have 'Diff' and 'Messages' in it along with the filename
    # or url.
    # The body should have each of five message types from pfif_object_diff
    for message in ['Diff', 'Messages', 'added_deleted_changed_1.xml',
                    'fake_url', 'extra', 'missing', 'field', 'record', 'Value',
                    'changed', 'A', 'B']:
      self.assertTrue(message in  response_str and message in
                      grouped_response_str, 'The diff was missing the '
                      'following message: ' + message + '.  The diff: ' +
                      response_str)

  def test_ignore_fields(self):
    """The diff results page should not include any fields that were passed in
    with ignore_fields."""
    request = {'pfif_xml_1' : PfifXml.XML_ADDED_DELETED_CHANGED_1,
               'pfif_xml_2' : PfifXml.XML_ADDED_DELETED_CHANGED_2,
               'options' : 'text_is_case_sensitive',
               'ignore_fields' : 'foo bar source_date'}
    response = self.make_request(request, path='/diff/results')
    response_str = response.content
    for field in ['foo', 'bar', 'source_date']:
      self.assertFalse(field in response_str, field + ' is ignored and should '
                       'not be in the response.')

  def test_missing_filenames(self):
    """The diff results page should fail gracefully when diffing a pasted in
    file, which has no filename."""
    response = self.make_request(
        {'pfif_xml_1' : PfifXml.XML_ADDED_DELETED_CHANGED_1,
         'pfif_xml_2' : PfifXml.XML_ADDED_DELETED_CHANGED_2},
        path='/diff/results')
    response_str = response.content
    self.assertTrue('pasted in' in response_str)

if __name__ == '__main__':
  unittest.main()
