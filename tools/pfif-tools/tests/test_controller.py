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

import unittest
import controller
from StringIO import StringIO
from google.appengine.ext import webapp
import tests.pfif_xml as PfifXml
import utils
from webob.multidict import MultiDict

class FakeFieldStorage(object):
  """A mock to test Field Storage files used in WebOb requests."""

  def __init__(self, filename, value):
    self.filename = filename
    self.value = value

  def __repr__(self):
    return self.value

class ControllerTests(unittest.TestCase):
  """Tests for the controller."""

  # pylint: disable=C0301
  # advice from
  # http://stackoverflow.com/questions/6222528/unittesting-the-webapp-requesthandler-in-gae-python
  # for testing webapp server
  # pylint: enable=C0301
  @staticmethod
  def make_webapp_request(content, handler_init_method=None):
    """Makes a webapp request for the validator with content as the HTTP POST
    content.  Returns the response."""
    if handler_init_method is None:
      handler_init_method = controller.ValidatorController
    request = webapp.Request({'wsgi.input' : StringIO(),
                              'REQUEST_METHOD' : 'POST',
                              'PATH_INFO' : '/validator'})
    for key, val in content.items():
      request.POST.add(key, val)
    response = webapp.Response()
    handler = handler_init_method()
    handler.initialize(request, response)
    handler.post()
    return response

  # file tests

  def test_no_xml_fails_gracefully(self):
    """If the user tries to validate with no input, there should not be an
    exception."""
    for handler_method in [controller.ValidatorController,
                           controller.DiffController]:
      response = self.make_webapp_request(
          {}, handler_init_method=handler_method)
      self.assertTrue("html" in response.out.getvalue())

  def test_pasting_xml(self):
    """The page should have the correct number of errors in the header when
    using the pfif_xml_1 POST variable to send PFIF XML."""
    response = self.make_webapp_request({'pfif_xml_1' :
                                         PfifXml.XML_TWO_DUPLICATE_NO_CHILD})
    self.assertTrue("3 Messages" in response.out.getvalue())

  def test_file_upload(self):
    """The page should have the correct number of errors in the header when
    using the pfif_xml_file_1 POST variable to send PFIF XML."""
    fake_file = FakeFieldStorage('two_duplicate_no_child.xml',
                                 PfifXml.XML_TWO_DUPLICATE_NO_CHILD)
    response = self.make_webapp_request({'pfif_xml_file_1' :
                                         fake_file})
    self.assertTrue("3 Messages" in response.out.getvalue())

  def test_url_upload(self):
    """The page should have the correct number of errors in the header when
    using the pfif_xml_url_1 POST variable to send PFIF XML."""
    utils.set_file_for_test(StringIO(PfifXml.XML_TWO_DUPLICATE_NO_CHILD))
    response = self.make_webapp_request({'pfif_xml_url_1' : 'dummy_url'})
    self.assertTrue("3 Messages" in response.out.getvalue())

  # validator

  def test_validator_options(self):
    """The validator results page should have a span or div for each print
    option."""
    fake_file = FakeFieldStorage('xml_expire_99_empty_data.xml',
                                 PfifXml.XML_EXPIRE_99_EMPTY_DATA)
    request = MultiDict({'pfif_xml_file_1' : fake_file})

    request['print_options'] = 'show_errors'
    response = self.make_webapp_request(request)
    self.assertTrue('ERROR' in response.out.getvalue())
    self.assertTrue('message_type' in response.out.getvalue())
    self.assertTrue('message_category' in response.out.getvalue())

    request.add('print_options', 'show_warnings')
    response = self.make_webapp_request(request)
    self.assertTrue('WARNING' in response.out.getvalue())

    request.add('print_options', 'show_line_numbers')
    response = self.make_webapp_request(request)
    self.assertTrue('message_line_number' in response.out.getvalue())

    request.add('print_options', 'show_record_ids')
    response = self.make_webapp_request(request)
    self.assertTrue('record_id' in response.out.getvalue())

    request.add('print_options', 'show_full_line')
    response = self.make_webapp_request(request)
    self.assertTrue('message_xml_full_line' in response.out.getvalue())

    # EXPIRE_99 doesn't have any errors with xml element text or tag, so we use
    # a different XML file
    fake_file = FakeFieldStorage('xml_incorrect_format_11.xml',
                                 PfifXml.XML_INCORRECT_FORMAT_11)
    request['pfif_xml_file_1'] = fake_file
    request.add('print_options', 'show_xml_tag')
    response = self.make_webapp_request(request)
    self.assertTrue('message_xml_tag' in response.out.getvalue())

    request.add('print_options', 'show_xml_text')
    response = self.make_webapp_request(request)
    self.assertTrue('message_xml_text' in response.out.getvalue())

  # diff

  def test_diff(self):
    """The diff results page should have a header and a div for each message."""
    fake_file_1 = FakeFieldStorage('added_deleted_changed_1.xml',
                                   PfifXml.XML_ADDED_DELETED_CHANGED_1)
    utils.set_file_for_test(StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_2))
    request = MultiDict({
        'pfif_xml_file_1' : fake_file_1, 'pfif_xml_url_2' : 'fake_url',
        'options' : 'text_is_case_sensitive'})
    response = self.make_webapp_request(
        request, handler_init_method=controller.DiffController)
    response_str = response.out.getvalue()

    # set the test file again because the first one will be at the end, and the
    # xml parser doesn't have to seek(0) on it.
    utils.set_file_for_test(StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_2))
    request.add('options', 'group_messages_by_record')
    grouped_response = self.make_webapp_request(
        request, handler_init_method=controller.DiffController)
    grouped_response_str = grouped_response.out.getvalue()

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
    response = self.make_webapp_request(
        request, handler_init_method=controller.DiffController)
    response_str = response.out.getvalue()
    for field in ['foo', 'bar', 'source_date']:
      self.assertFalse(field in response_str, field + ' is ignored and should '
                       'not be in the response.')

  def test_missing_filenames(self):
    """The diff results page should fail gracefully when diffing a pasted in
    file, which has no filename."""
    response = self.make_webapp_request(
        {'pfif_xml_1' : PfifXml.XML_ADDED_DELETED_CHANGED_1,
         'pfif_xml_2' : PfifXml.XML_ADDED_DELETED_CHANGED_2},
        handler_init_method=controller.DiffController)
    response_str = response.out.getvalue()
    self.assertTrue('pasted in' in response_str)

  @staticmethod
  def test_main():
    """main should not crash."""
    controller.main()

if __name__ == '__main__':
  unittest.main()
