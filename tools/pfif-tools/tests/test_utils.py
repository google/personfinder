#!/usr/bin/env python
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

"""Tests for utils.py"""

import utils
import unittest
from StringIO import StringIO
import tests.pfif_xml as PfifXml
import pfif_diff

class UtilTests(unittest.TestCase):
  """Defines tests for utils.py"""

  # extract_tag

  def test_blank_input(self):
    """extract_tag should return an empty string on blank input"""
    self.assertEqual(utils.extract_tag(""), "")

  def test_tag(self):
    """extract_tag should return the original string when the string does not
    start with a namespace"""
    self.assertEqual(utils.extract_tag("foo"), "foo")

  def test_tag_and_namespace(self):
    """extract_tag should return the local tag when the string starts with a
    namespace"""
    self.assertEqual(utils.extract_tag("{foo}bar"), "bar")

  # PfifXmlTree initialization

  def test_valid_xml(self):
    """initialize_xml should turn a string of valid XML into an object."""
    valid_xml_file = StringIO(PfifXml.XML_11_SMALL)
    tree = utils.PfifXmlTree(valid_xml_file)
    self.assertTrue(tree)
    self.assertTrue(tree.lines)
    self.assertTrue(tree.line_numbers)

  def test_invalid_xml(self):
    """initialize_xml should raise an error on a string of invalid XML."""
    invalid_xml_file = StringIO(PfifXml.XML_INVALID)
    self.assertRaises(Exception, utils.PfifXmlTree, invalid_xml_file)

  # PfifXmlTree.initialize_pfif_version

  def test_root_is_pfif(self):
    """initialize_pfif_version should return the version if the root is PFIF."""
    pfif_11_xml_file = StringIO(PfifXml.XML_11_SMALL)
    tree = utils.PfifXmlTree(pfif_11_xml_file)
    self.assertEqual(tree.version, 1.1)

  def test_root_is_not_pfif(self):
    """initialize_pfif_version should raise an exception if the XML root
    is not PFIF."""
    non_pfif_xml_file = StringIO(PfifXml.XML_NON_PFIF_ROOT)
    self.assertRaises(Exception, utils.PfifXmlTree, non_pfif_xml_file)

  def test_root_lacks_namespace(self):
    """initialize_pfif_version should raise an exception if the XML root
    doesn't specify a namespace."""
    no_namespace_xml_file = StringIO(PfifXml.XML_NO_NAMESPACE)
    self.assertRaises(Exception, utils.PfifXmlTree, no_namespace_xml_file)

  def test_root_is_bad_pfif_version(self):
    """initialize_pfif_version should raise an exception if the PFIF
    version is not supported."""
    pfif_99_xml_file = StringIO(PfifXml.XML_BAD_PFIF_VERSION)
    self.assertRaises(Exception, utils.PfifXmlTree, pfif_99_xml_file)

  def test_root_is_bad_pfif_website(self):
    """initialize_pfif_version should raise an exception if the PFIF
    website is wrong."""
    pfif_bad_website_xml_file = StringIO(PfifXml.XML_BAD_PFIF_WEBSITE)
    self.assertRaises(Exception, utils.PfifXmlTree, pfif_bad_website_xml_file)

  # MessagesOutput

  def test_group_messages_by_record(self):
    """group_messages_by_record should return a map from record_id to
    message."""
    messages = pfif_diff.pfif_file_diff(
        StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_1),
        StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_2))
    grouped_messages = utils.MessagesOutput.group_messages_by_record(messages)
    self.assertTrue('example.org/person1' in grouped_messages)
    self.assertTrue('example.org/person2' in grouped_messages)

  def test_group_messages_by_category(self):
    """group_messages_by_category should return a map from category to
    message."""
    messages = pfif_diff.pfif_file_diff(
        StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_1),
        StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_2))
    grouped_messages = utils.MessagesOutput.group_messages_by_category(messages)
    self.assertTrue(utils.Categories.ADDED_RECORD in grouped_messages)
    self.assertTrue(utils.Categories.ADDED_FIELD in grouped_messages)
    self.assertTrue(utils.Categories.DELETED_RECORD in grouped_messages)
    self.assertTrue(utils.Categories.DELETED_FIELD in grouped_messages)
    self.assertTrue(utils.Categories.CHANGED_FIELD in grouped_messages)

  def test_get_field_from_messages(self):
    """get_field_from_messages should return a list of all fields in the
    messages."""
    messages = pfif_diff.pfif_file_diff(
        StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_1),
        StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_2))

    # record_id should get person and note records
    record_ids = utils.MessagesOutput.get_field_from_messages(messages,
                                                              'record_id')
    self.assertTrue('example.org/person1' in record_ids)
    self.assertTrue('example.org/person2' in record_ids)

    # xml_tag should get all tags
    tags = utils.MessagesOutput.get_field_from_messages(messages, 'xml_tag')
    self.assertTrue('foo' in tags)
    self.assertTrue('bar' in tags)
    self.assertTrue('source_date' in tags)

  def test_messages_to_str_by_id(self):
    """messages_to_str_by_id should create one message for added records, one
    message for removed records, and one message for each other record."""
    # an empty messages list should produce no errors and return a string with
    # no messages
    output_str = utils.MessagesOutput.messages_to_str_by_id([], is_html=True)
    self.assertEqual(output_str.count('"message"'), 0)

    # there should be an added section, a deleted section, and one section for
    # each of the records that had fields added, removed, or changed
    messages = pfif_diff.pfif_file_diff(
        StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_1),
        StringIO(PfifXml.XML_ADDED_DELETED_CHANGED_2))
    output_str = utils.MessagesOutput.messages_to_str_by_id(messages,
                                                            is_html=True)
    self.assertEqual(output_str.count('grouped_record_header'), 3)
    self.assertEqual(output_str.count('"message"'), 3)
    self.assertTrue('foo' in output_str)
    self.assertTrue('bar' in output_str)
    self.assertTrue('source_date' in output_str)

    # when a field is added but no field is changed or deleted, there should
    # only be one section with one list.
    messages = pfif_diff.pfif_file_diff(
        StringIO(PfifXml.XML_ONE_PERSON_ONE_FIELD),
        StringIO(PfifXml.XML_ONE_PERSON_TWO_FIELDS))
    output_str = utils.MessagesOutput.messages_to_str_by_id(messages,
                                                            is_html=True)
    self.assertEqual(output_str.count('grouped_record_header'), 1)
    self.assertEqual(output_str.count('"message"'), 1)
    self.assertEqual(output_str.count('grouped_record_list'), 1)

  def test_truncate(self):
    """truncate should leave there with the specified number of messages per
    category (plus one for every category that was truncated)."""
    messages = [utils.Message('Category') for _ in range(3)]

    truncated_messages = utils.MessagesOutput.truncate(messages, 1)
    self.assertEqual(len(truncated_messages), 2)
    self.assertEqual(truncated_messages.count(utils.Message('Category')), 1)

if __name__ == '__main__':
  unittest.main()
