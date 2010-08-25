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

"""Tests for importer.py."""

import datetime
import unittest

from google.appengine.ext import db

import model
import importer


class ImporterTests(unittest.TestCase):
  """Test the import utilities."""

  def tearDown(self):
    db.delete(model.Person.all())
    db.delete(model.Note.all())

  def test_strip(self):
    self.assertEqual(importer.strip(""), "")
    self.assertEqual(importer.strip(None), "")
    self.assertEqual(importer.strip(0), "")
    self.assertEqual(importer.strip(" "), "")
    self.assertEqual(importer.strip(" \t"), "")
    self.assertEqual(importer.strip("\t "), "")
    self.assertEqual(importer.strip(" \n "), "")
    self.assertEqual(importer.strip("abc"), "abc")
    self.assertEqual(importer.strip("a b\tc "), "a b\tc")
    self.assertEqual(importer.strip(" a b\tc\t"), "a b\tc")

  def test_validate_datetime(self):
    self.assertEqual(importer.validate_datetime("2010-01-01T00:00:00Z"),
                     datetime.datetime(2010, 1, 1, 0, 0, 0))
    self.assertEqual(importer.validate_datetime("2010-01-01T01:23:45Z"),
                     datetime.datetime(2010, 1, 1, 1, 23, 45))

    self.assertEqual(importer.validate_datetime(""), None)
    self.assertEqual(importer.validate_datetime(0), None)

    self.assertRaises(ValueError, importer.validate_datetime, " ")
    self.assertRaises(ValueError, importer.validate_datetime, "2010-02-28")
    self.assertRaises(ValueError,
                      importer.validate_datetime,
                      "2010-02-28 01:23:45")
    self.assertRaises(ValueError,
                      importer.validate_datetime,
                      "2010-02-28 01:23:45Z")
    self.assertRaises(ValueError,
                      importer.validate_datetime,
                      "2010-02-28 1:23:45")

    # Invalid format
    self.assertRaises(ValueError,
                      importer.validate_datetime,
                      "2010-02-28T1:23:45Z")
    # Invalid date
    self.assertRaises(ValueError,
                      importer.validate_datetime,
                      "2010-02-29T01:23:45Z")
    # Invalid time
    self.assertRaises(ValueError,
                      importer.validate_datetime,
                      "2010-01-01T25:00:00Z")

  def test_validate_boolean(self):
    self.assertTrue(importer.validate_boolean("true"))
    self.assertTrue(importer.validate_boolean("TRUE"))
    self.assertTrue(importer.validate_boolean("True"))
    self.assertTrue(importer.validate_boolean("trUe"))
    self.assertTrue(importer.validate_boolean("1"))

    self.assertFalse(importer.validate_boolean("false"))
    self.assertFalse(importer.validate_boolean("ture"))
    self.assertFalse(importer.validate_boolean(""))
    self.assertFalse(importer.validate_boolean(None))
    self.assertFalse(importer.validate_boolean(1))

  def test_create_person(self):
    # clone record
    fields = {"first_name": " Zhi\n",
              "last_name": " Qiao",
              "person_record_id": "  test_domain/person_1 "}
    person = importer.create_person(None, fields)
    self.assertTrue(hasattr(person, "entry_date"))
    self.assertTrue(hasattr(person, "last_update_date"))
    self.assertEqual(person.first_name, "Zhi")
    self.assertEqual(person.last_name, "Qiao")
    self.assertEqual(person.person_record_id, "test_domain/person_1")
    self.assertEqual(person.key().kind(), 'Person')
    self.assertEqual(person.key().id(), None)
    self.assertEqual(person.key().name(), 'test_domain/person_1')

    # original record
    fields = {"first_name": " Zhi\n",
              "last_name": " Qiao",
              "person_record_id": model.HOME_DOMAIN + '/person.23 '}
    person = importer.create_person('haiti', fields)
    assert person.person_record_id.startswith(
        'haiti.' + model.HOME_DOMAIN + '/person.')

  def test_create_note(self):
    # clone record
    fields = {"note_record_id": " test_domain/note_1",
              "person_record_id": "  test_domain/person_1 "}
    note = importer.create_note(None, fields)
    self.assertEqual(note.note_record_id, "test_domain/note_1")
    self.assertEqual(note.person_record_id, "test_domain/person_1")
    self.assertEqual(note.status, "")
    self.assertEqual(note.key().kind(), 'Note')
    self.assertEqual(note.key().id(), None)
    self.assertEqual(note.key().name(), 'test_domain/note_1')

    # original record
    fields = {'note_record_id': model.HOME_DOMAIN + '/note.1',
              'person_record_id': "  test_domain/person_1 "}
    note = importer.create_note('haiti', fields)
    assert note.note_record_id.startswith(
        'haiti.' + model.HOME_DOMAIN + '/note.')
    assert note.person_record_id == 'test_domain/person_1'

  def test_import_person_records(self):
    records = []
    for i in range(20):
      first_name = "first_name_%d" % i
      last_name = "last_name_%d" % i

      source_date = "2010-01-01T01:23:45Z"
      record_id = "test_domain/%d" % i

      # Records 0, 8, and 16 have bad domains.
      if not i % 8:
        record_id = "other_domain/%d" % i
      # Records 0, 9, and 18 have invalid dates.
      elif not i % 9:
        source_date = "2010-01-01 01:23:45"

      records.append({"first_name": first_name,
                      "last_name": last_name,
                      "person_record_id": record_id,
                      "source_date": source_date})
    written, skipped, total = importer.import_records(
        'test_domain', importer.create_person, records)

    self.assertEqual(written, 15)
    self.assertEqual(len(skipped), 5)
    self.assertEqual(skipped[0], ("Not in authorized domain: u'other_domain/0'",
                                  {"first_name": "first_name_0",
                                   "last_name": "last_name_0",
                                   "source_date": "2010-01-01T01:23:45Z",
                                   "person_record_id": "other_domain/0"}))
    self.assertEqual(skipped[3],
                     ("Not in authorized domain: u'other_domain/16'",
                      {"first_name": "first_name_16",
                       "last_name": "last_name_16",
                       "source_date": "2010-01-01T01:23:45Z",
                       "person_record_id": "other_domain/16"}))
    self.assertEqual(skipped[2],
                     ("ValueError: Bad datetime: '2010-01-01 01:23:45'",
                      {"first_name": "first_name_9",
                       "last_name": "last_name_9",
                       "source_date": "2010-01-01 01:23:45",
                       "person_record_id": "test_domain/9"}))
    self.assertEqual(skipped[4],
                     ("ValueError: Bad datetime: '2010-01-01 01:23:45'",
                      {"first_name": "first_name_18",
                       "last_name": "last_name_18",
                       "source_date": "2010-01-01 01:23:45",
                       "person_record_id": "test_domain/18"}))
    self.assertEqual(total, 20)
    # Also confirm that 15 records were put into the datastore.
    self.assertEqual(model.Person.all().count(), 15)

  def test_import_note_records(self):
    records = []
    for i in range(20):
      source_date = "2010-01-01T01:23:45Z"
      note_id = "test_domain/record_%d" % i
      person_id = "test_domain/person_%d" % i

      # Records 0, 8, and 16 have bad note record domains.
      if not i % 8:
        note_id = "other_domain/record_%d" % i
      # Records 0, 9, and 18 have bad person record domains.
      # This should not matter for note records.
      elif not i % 9:
        person_id = "other_domain/person_%d" % i
      # Records 0, 5, 10, and 15 have invalid dates.
      elif not i % 5:
        source_date = "2010-01-01 01:23:45"

      records.append({"person_record_id": person_id,
                      "note_record_id": note_id,
                      "source_date": source_date})
    written, skipped, total = importer.import_records(
        'test_domain', importer.create_note, records)

    self.assertEqual(written, 14)
    self.assertEqual(len(skipped), 6)
    self.assertEqual(skipped[0],
                     ("Not in authorized domain: u'other_domain/record_0'",
                      {"person_record_id": "test_domain/person_0",
                       "source_date": "2010-01-01T01:23:45Z",
                       "note_record_id": "other_domain/record_0"}))
    self.assertEqual(skipped[2],
                     ("Not in authorized domain: u'other_domain/record_8'",
                      {"person_record_id": "test_domain/person_8",
                       "source_date": "2010-01-01T01:23:45Z",
                       "note_record_id": "other_domain/record_8"}))
    self.assertEqual(skipped[1],
                     ("ValueError: Bad datetime: '2010-01-01 01:23:45'",
                      {"person_record_id": "test_domain/person_5",
                       "source_date": "2010-01-01 01:23:45",
                       "note_record_id": "test_domain/record_5"}))
    self.assertEqual(skipped[4],
                     ("ValueError: Bad datetime: '2010-01-01 01:23:45'",
                      {"person_record_id": "test_domain/person_15",
                       "source_date": "2010-01-01 01:23:45",
                       "note_record_id": "test_domain/record_15"}))
    self.assertEqual(total, 20)
    # Also confirm that 14 records were put into the datastore.
    self.assertEqual(model.Note.all().count(), 14)


if __name__ == "__main__":
  unittest.main()
