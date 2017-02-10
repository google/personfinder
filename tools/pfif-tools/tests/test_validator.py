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

"""Tests for pfif_validator.py"""

import unittest
from StringIO import StringIO

import os
import sys
from pfif_validator import PfifValidator
import pfif_validator # to test main
import datetime
import utils
from utils import Message
import tests.pfif_xml as PfifXml

class ValidatorTests(unittest.TestCase):
  """Tests each validation function in pfif_validator.py"""

  EXPIRED_TIME = datetime.datetime(1999, 3, 1)

  PRINT_VALIDATOR_OUTPUT = True

  # Set Up

  def setUp(self): # pylint: disable=C0103
    """Some of the tests will run code that prints stuff out.  This prevents it
    from printing next to the clean dots from the unit tests."""
    if not ValidatorTests.PRINT_VALIDATOR_OUTPUT:
      sys.stdout = open(os.devnull, "w")

  @staticmethod
  def set_up_validator(xml):
    """Creates a PFIF validator from XML"""
    pfif_file = StringIO(xml)
    return PfifValidator(pfif_file)

  # printing

  def test_printing(self):
    """Tests that each of the printing options in set_printing_options changes
    the behavior of print_errors"""

    # set up the messages to be printed; the XML file here will not be used for
    # any tests.  It's just to get the validator initialized properly.
    validator = self.set_up_validator(PfifXml.XML_11_SMALL)
    lines = []
    for i in range(1, 12):
      lines.append('ZZZ ' + str(i))
    messages = []
    messages.append(Message("Message 1", is_error=True, xml_line_number=11,
                            xml_text="Text", person_record_id="Person",
                            note_record_id="Note"))
    messages.append(Message("Message 2", is_error=False))
    messages.append(Message("Message 3"))

    # With no errors or warnings, nothing should print
    output = validator.validator_messages_to_str(messages, show_errors=False,
                                       show_warnings=False)
    self.assertEqual(len(output), 0)

    # with only errors on, only errors should print
    output = validator.validator_messages_to_str(messages, show_warnings=False,
                                       show_line_numbers=False,
                                       show_record_ids=False,
                                       show_xml_text=False,
                                       show_full_line=False)
    self.assertNotEqual(output.find("Message 1"), -1)
    self.assertEqual(output.find("Message 2"), -1)
    # the default value of is_error should be True, so Message 3 should print
    self.assertNotEqual(output.find("Message 3"), -1)

    # with warnings on, warnings should print
    output = validator.validator_messages_to_str(
        messages, show_line_numbers=False, show_record_ids=False,
        show_xml_text=False, show_full_line=False)
    self.assertNotEqual(output.find("Message 2"), -1)

    # line numbers, xml text, and record IDs should not print with them off and
    # should print with them on
    self.assertEqual(output.find("11"), -1)
    output = validator.validator_messages_to_str(
        messages, show_line_numbers=True, show_record_ids=False,
        show_xml_text=False, show_full_line=False)
    self.assertNotEqual(output.find("11"), -1)

    self.assertEqual(output.find("Text"), -1)
    output = validator.validator_messages_to_str(
        messages, show_record_ids=False, show_xml_text=True,
        show_full_line=False)
    self.assertNotEqual(output.find("Text"), -1)

    self.assertEqual(output.find("Person"), -1)
    self.assertEqual(output.find("Note"), -1)
    output = validator.validator_messages_to_str(
        messages, show_record_ids=True, show_full_line=False)
    self.assertNotEqual(output.find("Person"), -1)
    self.assertNotEqual(output.find("Note"), -1)

    self.assertEqual(output.find("ZZZ 11"), -1)
    output = validator.validator_messages_to_str(
        messages, show_full_line=True, xml_lines=lines)
    self.assertNotEqual(output.find("ZZZ 11"), -1)

    # is_html should output a div somewhere
    self.assertEqual(output.find("div"), -1)
    output = validator.validator_messages_to_str(
        messages, is_html=True, xml_lines=lines)
    self.assertNotEqual(output.find("div"), -1)

  # validate_root_has_child

  def test_root_has_child(self):
    """validate_root_has_child should return an empty list if the root node has
    at least one child"""
    validator = self.set_up_validator(PfifXml.XML_11_SMALL)
    self.assertEqual(len(validator.validate_root_has_child()), 0)

  def test_root_lacks_child(self):
    """validate_root_has_child should return a list with a message if the root
    node does not have at least one child"""
    validator = self.set_up_validator(PfifXml.XML_ROOT_LACKS_CHILD)
    self.assertNotEqual(len(validator.validate_root_has_child()), 0)

  # validate_root_has_mandatory_children

  def test_root_has_mandatory_children(self):
    """validate_root_has_mandatory_children should return an empty list if one
    of the children is a person"""
    validator = self.set_up_validator(PfifXml.XML_11_SMALL)
    self.assertEqual(len(validator.validate_root_has_mandatory_children()), 0)

  def test_root_lacks_mandatory_children(self):
    """validate_root_has_mandatory_children should return a list with a message
    if the only children are not notes or persons"""
    validator = self.set_up_validator(PfifXml.XML_ROOT_HAS_BAD_CHILD)
    self.assertNotEqual(
        len(validator.validate_root_has_mandatory_children()), 0)

  def test_root_has_note_child_11(self):
    """validate_root_has_mandatory_children should return a list with a message
    if the only children are notes and the version is 1.1"""
    validator = self.set_up_validator(PfifXml.XML_TOP_LEVEL_NOTE_11)
    self.assertNotEqual(
        len(validator.validate_root_has_mandatory_children()), 0)

  def test_root_has_note_child_12(self):
    """validate_root_has_mandatory_children should return an empty list if the
    only children are notes and the version is greater than 1.1"""
    validator = self.set_up_validator(PfifXml.XML_TOP_LEVEL_NOTE_12)
    self.assertEqual(len(validator.validate_root_has_mandatory_children()), 0)

  # validate_has_mandatory_children

  def test_note_has_mandatory_children(self):
    """validate_has_mandatory_children should return an empty list if it is
    given notes with all mandatory children"""
    validator = self.set_up_validator(PfifXml.XML_NOTES_WITH_CHILDREN)
    self.assertEqual(len(validator.validate_note_has_mandatory_children()), 0)

  def test_note_has_no_mandatory_children(self):
    """validate_has_mandatory_children should return a list with nine missing
    children when given one child of a person with no children and one top level
    note (which also must have a person_record_id) with no children."""
    validator = self.set_up_validator(PfifXml.XML_NOTES_NO_CHILDREN)
    self.assertEqual(len(validator.validate_note_has_mandatory_children()), 9)

  def test_person_has_mandatory_children_11(self):
    """validate_has_mandatory_children should return an empty list if it is
    given a version 1.1 person with all mandatory children"""
    validator = self.set_up_validator(PfifXml.XML_PERSON_WITH_CHILDREN_11)
    self.assertEqual(len(validator.validate_person_has_mandatory_children()), 0)

  def test_person_has_mandatory_children_13(self):
    """validate_has_mandatory_children should return an empty list if it is
    given a version 1.3 person with all mandatory children"""
    validator = self.set_up_validator(PfifXml.XML_PERSON_WITH_CHILDREN_13)
    self.assertEqual(len(validator.validate_person_has_mandatory_children()), 0)

  def test_person_has_no_mandatory_children_11(self):
    """validate_has_mandatory_children should return a list with three missing
    children when given a version 1.1 person with no children"""
    validator = self.set_up_validator(PfifXml.XML_11_SMALL)
    self.assertEqual(len(validator.validate_person_has_mandatory_children()), 3)

  def test_person_has_no_mandatory_children_13(self):
    """validate_has_mandatory_children should return a list with three missing
    children when given a version 1.3 person with no children"""
    validator = self.set_up_validator(PfifXml.XML_PERSON_NO_CHILDREN_13)
    self.assertEqual(len(validator.validate_person_has_mandatory_children()), 3)

  # validate_fields_have_correct_format

  def test_no_fields_exist(self):
    """validate_fields_have_correct_format should return an empty list when
    passed a tree with no subelements of person or note because no nodes are
    improperly formatted."""
    validator = self.set_up_validator(PfifXml.XML_PERSON_NO_CHILDREN_13)
    self.assertEqual(len(validator.validate_fields_have_correct_format()), 0)
    validator = self.set_up_validator(PfifXml.XML_NOTES_NO_CHILDREN)
    self.assertEqual(len(validator.validate_fields_have_correct_format()), 0)

  def test_all_11_fields_have_correct_format(self):
    """validate_fields_have_correct_format should return an empty list when
    passed a tree with all 1.1 elements in the correct formats."""
    validator = self.set_up_validator(PfifXml.XML_11_FULL)
    self.assertEqual(len(validator.validate_fields_have_correct_format()), 0)

  #TODO(samking): test that non-ascii characters should be rejected
  def test_no_11_fields_have_correct_format(self):
    """validate_fields_have_correct_format should return a list with every
    subnode of person and note when every such subnode is of an incorrect
    format.  This tests all fields in version 1.1 for which incorrect input is
    possible."""
    validator = self.set_up_validator(PfifXml.XML_INCORRECT_FORMAT_11)
    self.assertEqual(len(validator.validate_fields_have_correct_format()), 23)

  def test_all_12_fields_have_correct_format(self):
    """validate_fields_have_correct_format should return an empty list when
    presented with a document where all fields have the correct format.  This
    tests all fields introduced or changed in 1.2; it does not test fields that
    were unchanged from 1.1."""
    validator = self.set_up_validator(PfifXml.XML_FULL_12)
    self.assertEqual(len(validator.validate_fields_have_correct_format()), 0)

  def test_no_12_fields_have_correct_format(self):
    """validate_fields_have_correct_format should return a list with every
    element presented to it when all fields have an incorrect format.  This
    tests all fields introduced or changed in 1.2, except ones that are always
    accepted; it does not test fields that were unchanged from 1.1."""
    validator = self.set_up_validator(PfifXml.XML_INCORRECT_FORMAT_12)
    self.assertEqual(len(validator.validate_fields_have_correct_format()), 12)

  def test_all_13_fields_have_correct_format(self):
    """validate_fields_have_correct_format should return an empty list when
    presented with a document where all fields have the correct format.  This
    tests all fields introduced or changed in 1.3; it does not test fields that
    were unchanged from 1.1 and 1.2."""
    validator = self.set_up_validator(PfifXml.XML_CORRECT_FORMAT_13)
    self.assertEqual(len(validator.validate_fields_have_correct_format()), 0)

  def test_no_13_fields_have_correct_format(self):
    """validate_fields_have_correct_format should return a list with every
    element presented to it when all fields have an incorrect format.  This
    tests all fields introduced or changed in 1.3, except ones that are always
    accepted; it does not test fields that were unchanged from 1.1 and 1.2."""
    validator = self.set_up_validator(PfifXml.XML_INCORRECT_FORMAT_13)
    self.assertEqual(len(validator.validate_fields_have_correct_format()), 1)

  # validate_unique_id
  def test_person_ids_are_unique(self):
    """validate_person_ids_are_unique should return an empty list when all
    person ids are unique"""
    validator = self.set_up_validator(PfifXml.XML_UNIQUE_PERSON_IDS)
    self.assertEqual(len(validator.validate_person_ids_are_unique()), 0)

  def test_note_ids_are_unique(self):
    """validate_note_ids_are_unique should return an empty list when all note
    ids are unique"""
    validator = self.set_up_validator(PfifXml.XML_UNIQUE_NOTE_IDS)
    self.assertEqual(len(validator.validate_note_ids_are_unique()), 0)

  def test_person_ids_are_not_unique(self):
    """validate_person_ids_are_unique should return a list with all non-unique
    person ids when there are non-unique person ids"""
    validator = self.set_up_validator(PfifXml.XML_DUPLICATE_PERSON_IDS)
    self.assertEqual(len(validator.validate_person_ids_are_unique()), 2)

  def test_note_ids_are_not_unique(self):
    """validate_person_ids_are_unique should return a list with all non-unique
    note ids when there are non-unique note ids"""
    validator = self.set_up_validator(PfifXml.XML_DUPLICATE_NOTE_IDS)
    self.assertEqual(len(validator.validate_note_ids_are_unique()), 2)

  # validate_notes_belong_to_persons

  def test_notes_belong_to_people(self):
    """validate_notes_belong_to_persons should return an empty list if all top
    level notes have a person_record_id and all notes inside persons have no
    person_record_id or the same person_record_id as the person."""
    validator = self.set_up_validator(PfifXml.XML_NOTES_BELONG_TO_PEOPLE)
    self.assertEqual(len(validator.validate_notes_belong_to_persons()), 0)

  def test_notes_do_not_belong_to_people(self):
    """validate_notes_belong_to_persons should return a list with all top level
    notes without a person_record_id and person_record_ids for notes that are
    under a person with a person_record_id that doesn't match the person"""
    validator = self.set_up_validator(PfifXml.XML_NOTES_WITHOUT_PEOPLE)
    self.assertEqual(len(validator.validate_notes_belong_to_persons()), 2)

  # validate_field_order

  def test_correct_field_order_11(self):
    """validate_person_field_order and validate_note_field_order should return
    a empty lists if all elements in all persons and notes are in the correct
    order"""
    validator = self.set_up_validator(PfifXml.XML_11_FULL)
    self.assertEqual(len(validator.validate_person_field_order()), 0)
    self.assertEqual(len(validator.validate_note_field_order()), 0)

  def test_omitting_fields_is_okay_11(self):
    """validate_person_field_order and validate_note_field_order should return
    a empty lists if all elements in all persons and notes are in the correct
    order, even if some elements are omitted (ie, 1,2,4 is in order even though
    3 is omitted)"""
    validator = self.set_up_validator(PfifXml.XML_MISSING_FIELDS_11)
    self.assertEqual(len(validator.validate_person_field_order()), 0)
    self.assertEqual(len(validator.validate_note_field_order()), 0)

  def test_incorrect_field_order_11(self):
    """validate_person_field_order and validate_note_field_order should return
    the first element in every person and note that are out of order"""
    validator = self.set_up_validator(PfifXml.XML_INCORRECT_FIELD_ORDER_11)
    self.assertEqual(len(validator.validate_person_field_order()), 3)
    self.assertEqual(len(validator.validate_note_field_order()), 2)

  def test_nonexistent_field(self):
    """validate_person_field_order and validate_note_field_order should ignore
    any fields that are not in the spec"""
    validator = self.set_up_validator(PfifXml.XML_EXTRANEOUS_FIELD_11)
    self.assertEqual(len(validator.validate_person_field_order()), 0)

  def test_correct_field_order_12(self):
    """validate_person_field_order and validate_note_field_order should return
    a empty lists if person_record_id comes first and any notes come last in
    persons and if note_record_id and person_record_id come first in notes."""
    validator = self.set_up_validator(PfifXml.XML_CORRECT_FIELD_ORDER_12)
    self.assertEqual(len(validator.validate_person_field_order()), 0)
    self.assertEqual(len(validator.validate_note_field_order()), 0)

  def test_incorrect_person_field_order_12(self):
    """validate_person_field_order should return a list with one entry for every
    person that does not have notes at the end or that does not have its
    person_record_id at the start"""
    validator = self.set_up_validator(
        PfifXml.XML_INCORRECT_PERSON_FIELD_ORDER_12)
    self.assertEqual(len(validator.validate_person_field_order()), 3)

  def test_incorrect_note_field_order_12(self):
    """validate_note_field_order should return a list with one entry for every
    note that does not have note_record_id and person_record_id at the start"""
    validator = self.set_up_validator(PfifXml.XML_INCORRECT_NOTE_FIELD_ORDER_12)
    self.assertEqual(len(validator.validate_note_field_order()), 4)

  def test_field_order_does_not_matter_13(self):
    """validate_person_field_order and validate_note_field_order should return
    an empty list if the version is greater than 1.2 because order doesn't
    matter"""
    validator = self.set_up_validator(PfifXml.XML_ODD_ORDER_13)
    self.assertEqual(len(validator.validate_person_field_order()), 0)
    self.assertEqual(len(validator.validate_note_field_order()), 0)

  # validate_expiry

  def test_unexpired_records(self):
    """validate_expired_records_removed should return an empty list when no
    records are expired"""
    validator = self.set_up_validator(
        PfifXml.XML_EXPIRE_99_HAS_DATA_NONSYNCED_DATES)
    not_expired_1998 = datetime.datetime(1998, 11, 1, 1, 1, 1, 1)
    utils.set_utcnow_for_test(not_expired_1998)
    self.assertEqual(len(validator.validate_expired_records_removed()), 0)
    just_not_expired = datetime.datetime(1999, 2, 4, 4, 5, 5, 0)
    utils.set_utcnow_for_test(just_not_expired)
    self.assertEqual(len(validator.validate_expired_records_removed()), 0)

  def test_expired_records_with_empty_data(self):
    """validate_expired_records_removed should return an empty list when all
    expired records have empty fields instead of real data"""
    validator = self.set_up_validator(PfifXml.XML_EXPIRE_99_EMPTY_DATA)
    utils.set_utcnow_for_test(ValidatorTests.EXPIRED_TIME)
    self.assertEqual(len(validator.validate_expired_records_removed()), 0)

  def test_expired_records_with_omissions(self):
    """validate_expired_records_removed should return an empty list when all
    expired records omit fields instead of exposing real data"""
    validator = self.set_up_validator(PfifXml.XML_EXPIRE_99_NO_DATA)
    utils.set_utcnow_for_test(ValidatorTests.EXPIRED_TIME)
    self.assertEqual(len(validator.validate_expired_records_removed()), 0)

  def test_expired_records_with_unremoved_data(self):
    """validate_expired_records_removed should return a list with the
    person_record_ids of all expired records that have data that should be
    removed"""
    validator = self.set_up_validator(
        PfifXml.XML_EXPIRE_99_HAS_NOTE_SYNCED_DATES)
    utils.set_utcnow_for_test(ValidatorTests.EXPIRED_TIME)
    self.assertEqual(len(validator.validate_expired_records_removed()), 1)
    just_expired = datetime.datetime(1999, 2, 4, 4, 5, 7)
    utils.set_utcnow_for_test(just_expired)
    self.assertEqual(len(validator.validate_expired_records_removed()), 1)

    validator = self.set_up_validator(
        PfifXml.XML_EXPIRE_99_HAS_DATA_SYNCED_DATES)
    utils.set_utcnow_for_test(ValidatorTests.EXPIRED_TIME)
    self.assertEqual(len(validator.validate_expired_records_removed()), 1)

  def test_expired_records_with_unremoved_top_level_note(self):
    """validate_expired_records_removed should return a list with messages for
    each expired record that still had a note referring to its
    person_record_id"""
    validator = (
        self.set_up_validator(PfifXml.XML_EXPIRE_99_HAS_NOTE_DATA))
    utils.set_utcnow_for_test(ValidatorTests.EXPIRED_TIME)
    self.assertEqual(len(validator.validate_expired_records_removed()), 1)

  def test_expiration_placeholder_with_bad_source_entry_date(self):
    """validate_expired_records_removed should return a list with the
    person_record_ids of all expired records whose source_date and entry_date
    are not the same value and are not created within a day after expiration"""
    validator = self.set_up_validator(
        PfifXml.XML_EXPIRE_99_NO_DATA_NONSYNCED_DATES)
    utils.set_utcnow_for_test(ValidatorTests.EXPIRED_TIME)
    self.assertEqual(len(validator.validate_expired_records_removed()), 2)

  def test_no_expiration_before_13(self):
    """validate_expired_records_removed should return an empty list when the
    version is before 1.3"""
    validator = self.set_up_validator(PfifXml.XML_EXPIRE_99_12)
    utils.set_utcnow_for_test(ValidatorTests.EXPIRED_TIME)
    self.assertEqual(len(validator.validate_expired_records_removed()), 0)

  def test_no_expiration_without_date(self):
    """validate_expired_records_removed should return an empty list when the
    there isn't an expiry_date"""
    validator = self.set_up_validator(PfifXml.XML_NO_EXPIRY_DATE)
    utils.set_utcnow_for_test(ValidatorTests.EXPIRED_TIME)
    self.assertEqual(len(validator.validate_expired_records_removed()), 0)

    validator = self.set_up_validator(PfifXml.XML_EMPTY_EXPIRY_DATE)
    utils.set_utcnow_for_test(ValidatorTests.EXPIRED_TIME)
    self.assertEqual(len(validator.validate_expired_records_removed()), 0)

  # validate_linked_person_records_are_matched

  def test_unlinked_records(self):
    """validate_linked_records_matched should return an empty list when
    evaluating unlinked persons"""
    validator = self.set_up_validator(PfifXml.XML_UNLINKED_RECORDS)
    self.assertEqual(len(validator.validate_linked_records_matched()), 0)

  def test_correctly_linked_records(self):
    """validate_linked_records_matched should return an empty list when
    evaluating two persons that each have notes with linked_person_record_ids
    pointing at each other"""
    validator = self.set_up_validator(PfifXml.XML_CORRECTLY_LINKED_RECORDS)
    self.assertEqual(len(validator.validate_linked_records_matched()), 0)

  def test_asymmetrically_linked_records(self):
    """validate_linked_records_matched should return a list with each
    note_record_id that has a linked_person_record_id that is not matched"""
    validator = self.set_up_validator(PfifXml.XML_ASYMMETRICALLY_LINKED_RECORDS)
    self.assertEqual(len(validator.validate_linked_records_matched()), 1)

  # validate_extraneous_fields

  def test_no_extra_fields(self):
    """validate_extraneous_fields should return an empty list when presented
    with a list that only includes fields in the PFIF spec"""
    validator = self.set_up_validator(PfifXml.XML_11_FULL)
    self.assertEqual(len(validator.validate_extraneous_fields()), 0)

  def test_gibberish_fields(self):
    """validate_extraneous_fields should return a list with every field that is
    not defined anywhere in the PFIF spec.  This includes fields defined in PFIF
    1.3 when using a 1.2 document."""
    validator = self.set_up_validator(PfifXml.XML_GIBBERISH_FIELDS)
    self.assertEqual(len(validator.validate_extraneous_fields()), 5)

  def test_duplicate_fields(self):
    """validate_extraneous_fields should return a list with every duplicated
    field (except for multiple <pfif:note> fields in one <pfif:person> or fields
    that are not at the same place in the tree, such as a note and a person with
    a person_record_id or two different notes)"""
    validator = self.set_up_validator(PfifXml.XML_DUPLICATE_FIELDS)
    self.assertEqual(len(validator.validate_extraneous_fields()), 3)

  def test_top_level_note_11(self):
    """validate_extraneous_fields should return a list with every top level note
    in a PFIF 1.1 document"""
    validator = self.set_up_validator(PfifXml.XML_TOP_LEVEL_NOTE_PERSON_11)
    self.assertEqual(len(validator.validate_extraneous_fields()), 2)

  # main application + run_validations

  def test_run_validations_without_errors(self):
    """run_validations should return an empty message list when passed a valid
    file"""
    validator = self.set_up_validator(PfifXml.XML_11_FULL)
    self.assertEqual(len(validator.run_validations()), 0)

  def test_run_validations_with_errors(self):
    """run_validations should return a message list with three errors when the
    root doesn't have a mandatory child and there are two duplicate nodes."""
    validator = self.set_up_validator(PfifXml.XML_TWO_DUPLICATE_NO_CHILD)
    self.assertEqual(len(validator.run_validations()), 3)

  def test_main_no_args(self):
    """main should give an assertion if it is given the wrong number of args."""
    old_argv = sys.argv
    sys.argv = ['pfif_validator.py']
    self.assertRaises(Exception, pfif_validator.main)
    sys.argv = old_argv

  def test_main(self):
    """main should not raise an exception under normal circumstances."""
    old_argv = sys.argv
    old_stdout = sys.stdout
    sys.argv = ['pfif_validator.py', 'mocked_file']
    sys.stdout = StringIO('')

    utils.set_file_for_test(StringIO(PfifXml.XML_11_FULL))
    pfif_validator.main()
    self.assertFalse('all_messages' in sys.stdout.getvalue())

    sys.stdout = old_stdout
    sys.argv = old_argv

  # line numbers

  def test_line_numbers(self):
    """After initialization, all elements in the tree should have line
    numbers in the map."""
    validator = self.set_up_validator(PfifXml.XML_FULL_12)
    nodes = validator.tree.get_all_persons()
    nodes.extend(validator.tree.get_all_notes())
    for node in nodes:
      self.assertTrue(node in validator.tree.line_numbers)
      for child in node.getchildren():
        self.assertTrue(child in validator.tree.line_numbers)

  # unicode

  def test_unicode_works(self):
    """none of the validations should fail when processing a field that includes
    unicode text."""
    validator = self.set_up_validator(PfifXml.XML_UNICODE_12)
    messages = validator.run_validations()
    validator.validator_messages_to_str(messages)
    self.assertEqual(len(messages), 0)

if __name__ == '__main__':
  unittest.main()
