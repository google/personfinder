# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS=" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = 'kpy@google.com (Ka-Ping Yee) and many other Googlers'

import StringIO
import difflib
import importer
import pfif
import pprint
import sys
import unittest

# utility function duplicated here from server_tests.
# TODO(lschumacher): find a happy place to share this.
def text_diff(expected, actual):
    """Produces a readable diff between two text strings."""
    if isinstance(expected, unicode):
        expected = expected.encode('ascii', 'ignore')
    if isinstance(actual, unicode):
        actual = actual.encode('ascii', 'ignore')
    return ''.join(difflib.context_diff(
            expected.splitlines(True), actual.splitlines(True),
            'expected', 'actual'))
    
def pprint_diff(expected, actual):
    """Produces a readable diff between two objects' printed representations."""
    return text_diff(pprint.pformat(expected), pprint.pformat(actual))

def dict_to_entity(dict):
    """Converts a dictionary to a fake entity."""
    PARSERS = {
        'source_date': importer.validate_datetime,
        'entry_date': importer.validate_datetime,
        'expiry_date': importer.validate_datetime,
        'found': importer.validate_boolean
    }

    class Entity:
        pass

    entity = Entity()
    for key in dict:
        setattr(entity, key, PARSERS.get(key, pfif.nop)(dict[key]))
    return entity


class TestCase:
    """A container for test data and expected results."""
    def __init__(self, pfif_version, xml, person_records=[], note_records=[],
                 do_parse_test=True, do_write_test=True, is_expired=False):
        self.pfif_version = pfif_version
        self.xml = xml
        self.person_records = person_records
        self.note_records = note_records

        # If true: parse self.xml, expect person_records and note_records.
        self.do_parse_test = do_parse_test

        # If true: serialize person_records and note_records, expect self.xml.
        self.do_write_test = do_write_test

        # If true: set the expired flag when serializing. 
        self.is_expired = is_expired


# The tests iterate over this list of TestCases and check each one.  Testing
# changes to PFIF should just require appending new TestCases to this list.
TEST_CASES = []

# The records corresponding to the PFIF 1.3 XML documents below.
PERSON_RECORD_1_3 = {
    u'person_record_id': u'test.google.com/person.21009',
    u'entry_date': u'2010-01-16T02:07:57Z',
    u'expiry_date': u'2010-02-16T02:07:57Z',
    u'author_name': u'_test_author_name',
    u'author_email': u'_test_author_email',
    u'author_phone': u'_test_author_phone',
    u'source_name': u'_test_source_name',
    u'source_date': u'2000-01-01T00:00:00Z',
    u'source_url': u'_test_source_url',
    u'first_name': u'_test_first_name',
    u'last_name': u'_test_last_name',
    u'full_name': u'_test_first_name_dot_last_name',
    u'sex': u'female',
    u'date_of_birth': u'1970-01-01',
    u'age': u'35-45',
    u'home_street': u'_test_home_street',
    u'home_neighborhood': u'_test_home_neighborhood',
    u'home_city': u'_test_home_city',
    u'home_state': u'_test_home_state',
    u'home_postal_code': u'_test_home_postal_code',
    u'home_country': u'US',
    u'photo_url': u'_test_photo_url',
    u'other': u'description:\n    _test_description & < > "\n',
}

PERSON_RECORD_EXPIRED_1_3 = {
    u'person_record_id': u'test.google.com/person.21009',
    u'entry_date': u'2010-01-16T02:07:57Z',
    u'expiry_date': u'2010-02-16T02:07:57Z',
    u'source_date': u'2000-01-01T00:00:00Z',
}

NOTE_RECORD_1_3 = {
    u'note_record_id': u'test.google.com/note.27009',
    u'person_record_id': u'test.google.com/person.21009',
    u'linked_person_record_id': u'test.google.com/person.777',
    u'entry_date': u'2010-01-16T17:32:05Z',
    u'author_name': u'_test_author_name',
    u'author_email': u'_test_author_email',
    u'author_phone': u'_test_author_phone',
    u'source_date': u'2000-02-02T02:02:02Z',
    u'found': u'true',
    u'status': u'believed_alive',
    u'email_of_found_person': u'_test_email_of_found_person',
    u'phone_of_found_person': u'_test_phone_of_found_person',
    u'last_known_location': u'_test_last_known_location',
    u'text': u'_test_text\n    line two\n',
}

TEST_CASES.append((
    'PFIF 1.3 with tag prefixes',
    TestCase('1.3', '''\
<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.21009</pfif:person_record_id>
    <pfif:entry_date>2010-01-16T02:07:57Z</pfif:entry_date>
    <pfif:expiry_date>2010-02-16T02:07:57Z</pfif:expiry_date>
    <pfif:author_name>_test_author_name</pfif:author_name>
    <pfif:author_email>_test_author_email</pfif:author_email>
    <pfif:author_phone>_test_author_phone</pfif:author_phone>
    <pfif:source_name>_test_source_name</pfif:source_name>
    <pfif:source_date>2000-01-01T00:00:00Z</pfif:source_date>
    <pfif:source_url>_test_source_url</pfif:source_url>
    <pfif:full_name>_test_first_name_dot_last_name</pfif:full_name>
    <pfif:first_name>_test_first_name</pfif:first_name>
    <pfif:last_name>_test_last_name</pfif:last_name>
    <pfif:sex>female</pfif:sex>
    <pfif:date_of_birth>1970-01-01</pfif:date_of_birth>
    <pfif:age>35-45</pfif:age>
    <pfif:home_street>_test_home_street</pfif:home_street>
    <pfif:home_neighborhood>_test_home_neighborhood</pfif:home_neighborhood>
    <pfif:home_city>_test_home_city</pfif:home_city>
    <pfif:home_state>_test_home_state</pfif:home_state>
    <pfif:home_postal_code>_test_home_postal_code</pfif:home_postal_code>
    <pfif:home_country>US</pfif:home_country>
    <pfif:photo_url>_test_photo_url</pfif:photo_url>
    <pfif:other>description:
    _test_description &amp; &lt; &gt; "
</pfif:other>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.27009</pfif:note_record_id>
      <pfif:person_record_id>test.google.com/person.21009</pfif:person_record_id>
      <pfif:linked_person_record_id>test.google.com/person.777</pfif:linked_person_record_id>
      <pfif:entry_date>2010-01-16T17:32:05Z</pfif:entry_date>
      <pfif:author_name>_test_author_name</pfif:author_name>
      <pfif:author_email>_test_author_email</pfif:author_email>
      <pfif:author_phone>_test_author_phone</pfif:author_phone>
      <pfif:source_date>2000-02-02T02:02:02Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:status>believed_alive</pfif:status>
      <pfif:email_of_found_person>_test_email_of_found_person</pfif:email_of_found_person>
      <pfif:phone_of_found_person>_test_phone_of_found_person</pfif:phone_of_found_person>
      <pfif:last_known_location>_test_last_known_location</pfif:last_known_location>
      <pfif:text>_test_text
    line two
</pfif:text>
    </pfif:note>
  </pfif:person>
</pfif:pfif>
''', [PERSON_RECORD_1_3], [NOTE_RECORD_1_3])))

TEST_CASES.append((
    'PFIF 1.3 with tag prefixes, with the person_record_id after the note',
    TestCase('1.3', '''\
<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:entry_date>2010-01-16T02:07:57Z</pfif:entry_date>
    <pfif:expiry_date>2010-02-16T02:07:57Z</pfif:expiry_date>
    <pfif:author_name>_test_author_name</pfif:author_name>
    <pfif:author_email>_test_author_email</pfif:author_email>
    <pfif:author_phone>_test_author_phone</pfif:author_phone>
    <pfif:source_name>_test_source_name</pfif:source_name>
    <pfif:source_date>2000-01-01T00:00:00Z</pfif:source_date>
    <pfif:source_url>_test_source_url</pfif:source_url>
    <pfif:full_name>_test_first_name_dot_last_name</pfif:full_name>
    <pfif:first_name>_test_first_name</pfif:first_name>
    <pfif:last_name>_test_last_name</pfif:last_name>
    <pfif:sex>female</pfif:sex>
    <pfif:date_of_birth>1970-01-01</pfif:date_of_birth>
    <pfif:age>35-45</pfif:age>
    <pfif:home_street>_test_home_street</pfif:home_street>
    <pfif:home_neighborhood>_test_home_neighborhood</pfif:home_neighborhood>
    <pfif:home_city>_test_home_city</pfif:home_city>
    <pfif:home_state>_test_home_state</pfif:home_state>
    <pfif:home_postal_code>_test_home_postal_code</pfif:home_postal_code>
    <pfif:home_country>US</pfif:home_country>
    <pfif:photo_url>_test_photo_url</pfif:photo_url>
    <pfif:other>description:
    _test_description &amp; &lt; &gt; "
</pfif:other>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.27009</pfif:note_record_id>
      <pfif:person_record_id>test.google.com/person.21009</pfif:person_record_id>
      <pfif:linked_person_record_id>test.google.com/person.777</pfif:linked_person_record_id>
      <pfif:entry_date>2010-01-16T17:32:05Z</pfif:entry_date>
      <pfif:author_name>_test_author_name</pfif:author_name>
      <pfif:author_email>_test_author_email</pfif:author_email>
      <pfif:author_phone>_test_author_phone</pfif:author_phone>
      <pfif:source_date>2000-02-02T02:02:02Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:status>believed_alive</pfif:status>
      <pfif:email_of_found_person>_test_email_of_found_person</pfif:email_of_found_person>
      <pfif:phone_of_found_person>_test_phone_of_found_person</pfif:phone_of_found_person>
      <pfif:last_known_location>_test_last_known_location</pfif:last_known_location>
      <pfif:text>_test_text
    line two
</pfif:text>
    </pfif:note>
    <pfif:person_record_id>test.google.com/person.21009</pfif:person_record_id>
  </pfif:person>
</pfif:pfif>
''', [PERSON_RECORD_1_3], [NOTE_RECORD_1_3], True, False)))

TEST_CASES.append((
    'PFIF 1.3 with notes only',
    TestCase('1.3', '''\
<?xml version="1.0" encoding="UTF-8"?>
<pfif xmlns="http://zesty.ca/pfif/1.3">
  <note>
    <note_record_id>test.google.com/note.27009</note_record_id>
    <person_record_id>test.google.com/person.21009</person_record_id>
    <linked_person_record_id>test.google.com/person.777</linked_person_record_id>
    <entry_date>2010-01-16T17:32:05Z</entry_date>
    <author_name>_test_author_name</author_name>
    <author_email>_test_author_email</author_email>
    <author_phone>_test_author_phone</author_phone>
    <source_date>2000-02-02T02:02:02Z</source_date>
    <found>true</found>
    <status>believed_alive</status>
    <email_of_found_person>_test_email_of_found_person</email_of_found_person>
    <phone_of_found_person>_test_phone_of_found_person</phone_of_found_person>
    <last_known_location>_test_last_known_location</last_known_location>
    <text>_test_text
    line two
</text>
  </note>
</pfif>
''', [], [NOTE_RECORD_1_3], True, False)))

TEST_CASES.append((
    'PFIF 1.3 for an expired record with data that should be hidden',
    TestCase('1.3', '''\
<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.21009</pfif:person_record_id>
    <pfif:entry_date>2010-01-16T02:07:57Z</pfif:entry_date>
    <pfif:expiry_date>2010-02-16T02:07:57Z</pfif:expiry_date>
    <pfif:source_date>2000-01-01T00:00:00Z</pfif:source_date>
    <pfif:full_name></pfif:full_name>
  </pfif:person>
</pfif:pfif>
''', [PERSON_RECORD_1_3], [], False, True, True)))

TEST_CASES.append((
    'PFIF 1.3 for an expired record with data that has been wiped',
    TestCase('1.3', '''\
<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.21009</pfif:person_record_id>
    <pfif:entry_date>2010-01-16T02:07:57Z</pfif:entry_date>
    <pfif:expiry_date>2010-02-16T02:07:57Z</pfif:expiry_date>
    <pfif:source_date>2000-01-01T00:00:00Z</pfif:source_date>
    <pfif:full_name></pfif:full_name>
  </pfif:person>
</pfif:pfif>
''', [PERSON_RECORD_EXPIRED_1_3], [], True, True, True)))



# The records corresponding to the PFIF 1.2 XML documents below.
PERSON_RECORD_1_2 = {
    u'person_record_id': u'test.google.com/person.21009',
    u'entry_date': u'2010-01-16T02:07:57Z',
    u'author_name': u'_test_author_name',
    u'author_email': u'_test_author_email',
    u'author_phone': u'_test_author_phone',
    u'source_name': u'_test_source_name',
    u'source_date': u'2000-01-01T00:00:00Z',
    u'source_url': u'_test_source_url',
    u'first_name': u'_test_first_name',
    u'last_name': u'_test_last_name',
    u'sex': u'female',
    u'date_of_birth': u'1970-01-01',
    u'age': u'35-45',
    u'home_street': u'_test_home_street',
    u'home_neighborhood': u'_test_home_neighborhood',
    u'home_city': u'_test_home_city',
    u'home_state': u'_test_home_state',
    u'home_postal_code': u'_test_home_postal_code',
    u'home_country': u'US',
    u'photo_url': u'_test_photo_url',
    u'other': u'description:\n    _test_description & < > "\n',
}

NOTE_RECORD_1_2 = {
    u'note_record_id': u'test.google.com/note.27009',
    u'person_record_id': u'test.google.com/person.21009',
    u'linked_person_record_id': u'test.google.com/person.777',
    u'entry_date': u'2010-01-16T17:32:05Z',
    u'author_name': u'_test_author_name',
    u'author_email': u'_test_author_email',
    u'author_phone': u'_test_author_phone',
    u'source_date': u'2000-02-02T02:02:02Z',
    u'found': u'true',
    u'status': u'believed_alive',
    u'email_of_found_person': u'_test_email_of_found_person',
    u'phone_of_found_person': u'_test_phone_of_found_person',
    u'last_known_location': u'_test_last_known_location',
    u'text': u'_test_text\n    line two\n',
}

TEST_CASES.append((
    'PFIF 1.2 XML document with tag prefixes',
    TestCase('1.2', '''\
<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.21009</pfif:person_record_id>
    <pfif:entry_date>2010-01-16T02:07:57Z</pfif:entry_date>
    <pfif:author_name>_test_author_name</pfif:author_name>
    <pfif:author_email>_test_author_email</pfif:author_email>
    <pfif:author_phone>_test_author_phone</pfif:author_phone>
    <pfif:source_name>_test_source_name</pfif:source_name>
    <pfif:source_date>2000-01-01T00:00:00Z</pfif:source_date>
    <pfif:source_url>_test_source_url</pfif:source_url>
    <pfif:first_name>_test_first_name</pfif:first_name>
    <pfif:last_name>_test_last_name</pfif:last_name>
    <pfif:sex>female</pfif:sex>
    <pfif:date_of_birth>1970-01-01</pfif:date_of_birth>
    <pfif:age>35-45</pfif:age>
    <pfif:home_street>_test_home_street</pfif:home_street>
    <pfif:home_neighborhood>_test_home_neighborhood</pfif:home_neighborhood>
    <pfif:home_city>_test_home_city</pfif:home_city>
    <pfif:home_state>_test_home_state</pfif:home_state>
    <pfif:home_postal_code>_test_home_postal_code</pfif:home_postal_code>
    <pfif:home_country>US</pfif:home_country>
    <pfif:photo_url>_test_photo_url</pfif:photo_url>
    <pfif:other>description:
    _test_description &amp; &lt; &gt; "
</pfif:other>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.27009</pfif:note_record_id>
      <pfif:person_record_id>test.google.com/person.21009</pfif:person_record_id>
      <pfif:linked_person_record_id>test.google.com/person.777</pfif:linked_person_record_id>
      <pfif:entry_date>2010-01-16T17:32:05Z</pfif:entry_date>
      <pfif:author_name>_test_author_name</pfif:author_name>
      <pfif:author_email>_test_author_email</pfif:author_email>
      <pfif:author_phone>_test_author_phone</pfif:author_phone>
      <pfif:source_date>2000-02-02T02:02:02Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:status>believed_alive</pfif:status>
      <pfif:email_of_found_person>_test_email_of_found_person</pfif:email_of_found_person>
      <pfif:phone_of_found_person>_test_phone_of_found_person</pfif:phone_of_found_person>
      <pfif:last_known_location>_test_last_known_location</pfif:last_known_location>
      <pfif:text>_test_text
    line two
</pfif:text>
    </pfif:note>
  </pfif:person>
</pfif:pfif>
''', [PERSON_RECORD_1_2], [NOTE_RECORD_1_2])))

TEST_CASES.append((
    'PFIF 1.2 XML document without tag prefixes',
    TestCase('1.2', '''\
<?xml version="1.0" encoding="UTF-8"?>
<pfif xmlns="http://zesty.ca/pfif/1.2">
  <person>
    <person_record_id>test.google.com/person.21009</person_record_id>
    <entry_date>2010-01-16T02:07:57Z</entry_date>
    <author_name>_test_author_name</author_name>
    <author_email>_test_author_email</author_email>
    <author_phone>_test_author_phone</author_phone>
    <source_name>_test_source_name</source_name>
    <source_date>2000-01-01T00:00:00Z</source_date>
    <source_url>_test_source_url</source_url>
    <first_name>_test_first_name</first_name>
    <last_name>_test_last_name</last_name>
    <sex>female</sex>
    <date_of_birth>1970-01-01</date_of_birth>
    <age>35-45</age>
    <home_street>_test_home_street</home_street>
    <home_neighborhood>_test_home_neighborhood</home_neighborhood>
    <home_city>_test_home_city</home_city>
    <home_state>_test_home_state</home_state>
    <home_postal_code>_test_home_postal_code</home_postal_code>
    <home_country>US</home_country>
    <photo_url>_test_photo_url</photo_url>
    <other>description:
    _test_description &amp; &lt; &gt; "
</other>
    <note>
      <note_record_id>test.google.com/note.27009</note_record_id>
      <person_record_id>test.google.com/person.21009</person_record_id>
      <linked_person_record_id>test.google.com/person.777</linked_person_record_id>
      <entry_date>2010-01-16T17:32:05Z</entry_date>
      <author_name>_test_author_name</author_name>
      <author_email>_test_author_email</author_email>
      <author_phone>_test_author_phone</author_phone>
      <source_date>2000-02-02T02:02:02Z</source_date>
      <found>true</found>
      <status>believed_alive</status>
      <email_of_found_person>_test_email_of_found_person</email_of_found_person>
      <phone_of_found_person>_test_phone_of_found_person</phone_of_found_person>
      <last_known_location>_test_last_known_location</last_known_location>
      <text>_test_text
    line two
</text>
    </note>
  </person>
</pfif>
''', [PERSON_RECORD_1_2], [NOTE_RECORD_1_2], True, False)))

TEST_CASES.append((
    'PFIF 1.2 with tag prefixes, with the person_record_id after the note',
    TestCase('1.2', '''\
<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:entry_date>2010-01-16T02:07:57Z</pfif:entry_date>
    <pfif:author_name>_test_author_name</pfif:author_name>
    <pfif:author_email>_test_author_email</pfif:author_email>
    <pfif:author_phone>_test_author_phone</pfif:author_phone>
    <pfif:source_name>_test_source_name</pfif:source_name>
    <pfif:source_date>2000-01-01T00:00:00Z</pfif:source_date>
    <pfif:source_url>_test_source_url</pfif:source_url>
    <pfif:first_name>_test_first_name</pfif:first_name>
    <pfif:last_name>_test_last_name</pfif:last_name>
    <pfif:sex>female</pfif:sex>
    <pfif:date_of_birth>1970-01-01</pfif:date_of_birth>
    <pfif:age>35-45</pfif:age>
    <pfif:home_street>_test_home_street</pfif:home_street>
    <pfif:home_neighborhood>_test_home_neighborhood</pfif:home_neighborhood>
    <pfif:home_city>_test_home_city</pfif:home_city>
    <pfif:home_state>_test_home_state</pfif:home_state>
    <pfif:home_postal_code>_test_home_postal_code</pfif:home_postal_code>
    <pfif:home_country>US</pfif:home_country>
    <pfif:photo_url>_test_photo_url</pfif:photo_url>
    <pfif:other>description:
    _test_description &amp; &lt; &gt; "
</pfif:other>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.27009</pfif:note_record_id>
      <pfif:person_record_id>test.google.com/person.21009</pfif:person_record_id>
      <pfif:linked_person_record_id>test.google.com/person.777</pfif:linked_person_record_id>
      <pfif:entry_date>2010-01-16T17:32:05Z</pfif:entry_date>
      <pfif:author_name>_test_author_name</pfif:author_name>
      <pfif:author_email>_test_author_email</pfif:author_email>
      <pfif:author_phone>_test_author_phone</pfif:author_phone>
      <pfif:source_date>2000-02-02T02:02:02Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:status>believed_alive</pfif:status>
      <pfif:email_of_found_person>_test_email_of_found_person</pfif:email_of_found_person>
      <pfif:phone_of_found_person>_test_phone_of_found_person</pfif:phone_of_found_person>
      <pfif:last_known_location>_test_last_known_location</pfif:last_known_location>
      <pfif:text>_test_text
    line two
</pfif:text>
    </pfif:note>
    <pfif:person_record_id>test.google.com/person.21009</pfif:person_record_id>
  </pfif:person>
</pfif:pfif>
''', [PERSON_RECORD_1_2], [NOTE_RECORD_1_2], True, False)))

TEST_CASES.append((
    'PFIF 1.2 XML document with notes only',
    TestCase('1.2', '''\
<?xml version="1.0" encoding="UTF-8"?>
<pfif xmlns="http://zesty.ca/pfif/1.2">
  <note>
    <note_record_id>test.google.com/note.27009</note_record_id>
    <person_record_id>test.google.com/person.21009</person_record_id>
    <linked_person_record_id>test.google.com/person.777</linked_person_record_id>
    <entry_date>2010-01-16T17:32:05Z</entry_date>
    <author_name>_test_author_name</author_name>
    <author_email>_test_author_email</author_email>
    <author_phone>_test_author_phone</author_phone>
    <source_date>2000-02-02T02:02:02Z</source_date>
    <found>true</found>
    <status>believed_alive</status>
    <email_of_found_person>_test_email_of_found_person</email_of_found_person>
    <phone_of_found_person>_test_phone_of_found_person</phone_of_found_person>
    <last_known_location>_test_last_known_location</last_known_location>
    <text>_test_text
    line two
</text>
  </note>
</pfif>
''', [], [NOTE_RECORD_1_2], True, False)))


# The records corresponding to the PFIF 1.1 XML documents below.
PERSON_RECORD_1_1 = {
    u'person_record_id': u'test.google.com/person.21009',
    u'entry_date': u'2010-01-16T02:07:57Z',
    u'author_name': u'_test_author_name',
    u'author_email': u'_test_author_email',
    u'author_phone': u'_test_author_phone',
    u'source_name': u'_test_source_name',
    u'source_date': u'2000-01-01T00:00:00Z',
    u'source_url': u'_test_source_url',
    u'first_name': u'_test_first_name',
    u'last_name': u'_test_last_name',
    u'home_street': u'_test_home_street',
    u'home_neighborhood': u'_test_home_neighborhood',
    u'home_city': u'_test_home_city',
    u'home_state': u'_test_home_state',
    u'home_zip': u'_test_home_zip',
    u'photo_url': u'_test_photo_url',
    u'other': u'description:\n    _test_description & < > "\n',
}

NOTE_RECORD_1_1 = {
    u'note_record_id': u'test.google.com/note.27009',
    u'person_record_id': u'test.google.com/person.21009',
    u'entry_date': u'2010-01-16T17:32:05Z',
    u'author_name': u'_test_author_name',
    u'author_email': u'_test_author_email',
    u'author_phone': u'_test_author_phone',
    u'source_date': u'2000-02-02T02:02:02Z',
    u'found': u'true',
    u'email_of_found_person': u'_test_email_of_found_person',
    u'phone_of_found_person': u'_test_phone_of_found_person',
    u'last_known_location': u'_test_last_known_location',
    u'text': u'_test_text\n    line two\n',
}

TEST_CASES.append((
    'PFIF 1.1 XML document with tag prefixes',
    TestCase('1.1', '''\
<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.21009</pfif:person_record_id>
    <pfif:entry_date>2010-01-16T02:07:57Z</pfif:entry_date>
    <pfif:author_name>_test_author_name</pfif:author_name>
    <pfif:author_email>_test_author_email</pfif:author_email>
    <pfif:author_phone>_test_author_phone</pfif:author_phone>
    <pfif:source_name>_test_source_name</pfif:source_name>
    <pfif:source_date>2000-01-01T00:00:00Z</pfif:source_date>
    <pfif:source_url>_test_source_url</pfif:source_url>
    <pfif:first_name>_test_first_name</pfif:first_name>
    <pfif:last_name>_test_last_name</pfif:last_name>
    <pfif:home_city>_test_home_city</pfif:home_city>
    <pfif:home_state>_test_home_state</pfif:home_state>
    <pfif:home_neighborhood>_test_home_neighborhood</pfif:home_neighborhood>
    <pfif:home_street>_test_home_street</pfif:home_street>
    <pfif:home_zip>_test_home_zip</pfif:home_zip>
    <pfif:photo_url>_test_photo_url</pfif:photo_url>
    <pfif:other>description:
    _test_description &amp; &lt; &gt; "
</pfif:other>
    <pfif:note>
      <pfif:note_record_id>test.google.com/note.27009</pfif:note_record_id>
      <pfif:entry_date>2010-01-16T17:32:05Z</pfif:entry_date>
      <pfif:author_name>_test_author_name</pfif:author_name>
      <pfif:author_email>_test_author_email</pfif:author_email>
      <pfif:author_phone>_test_author_phone</pfif:author_phone>
      <pfif:source_date>2000-02-02T02:02:02Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:email_of_found_person>_test_email_of_found_person</pfif:email_of_found_person>
      <pfif:phone_of_found_person>_test_phone_of_found_person</pfif:phone_of_found_person>
      <pfif:last_known_location>_test_last_known_location</pfif:last_known_location>
      <pfif:text>_test_text
    line two
</pfif:text>
    </pfif:note>
  </pfif:person>
</pfif:pfif>
''', [PERSON_RECORD_1_1], [NOTE_RECORD_1_1])))

# The record corresponding to the document below with non-ASCII characters.
PERSON_RECORD_WITH_NON_ASCII = {
    'person_record_id': 'test.google.com/person.123',
    'author_name': u'a with acute = \u00e1',
    'author_email': u'c with cedilla = \u00e7',
    'author_phone': u'e with acute = \u00e9',
    'first_name': u'greek alpha = \u03b1',
    'last_name': u'hebrew alef = \u05d0'
}

# A PFIF document containing some non-ASCII characters in UTF-8 encoding.
TEST_CASES.append((
    'PFIF 1.2 with non-ASCII characters',
    TestCase('1.2', '''\
<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id>test.google.com/person.123</pfif:person_record_id>
    <pfif:author_name>a with acute = \xc3\xa1</pfif:author_name>
    <pfif:author_email>c with cedilla = \xc3\xa7</pfif:author_email>
    <pfif:author_phone>e with acute = \xc3\xa9</pfif:author_phone>
    <pfif:first_name>greek alpha = \xce\xb1</pfif:first_name>
    <pfif:last_name>hebrew alef = \xd7\x90</pfif:last_name>
  </pfif:person>
</pfif:pfif>
''', [PERSON_RECORD_WITH_NON_ASCII], [])))


class PfifTests(unittest.TestCase):
    """Iterates over the TestCases and tests reading, writing, and parsing."""

    def test_parse_strings(self):
        """Tests XML parsing for each test case."""
        for test_name, test_case in TEST_CASES:
            if not test_case.do_parse_test:
                continue
            person_records, note_records = pfif.parse(test_case.xml)
            assert person_records == test_case.person_records, (test_name +
                ':\n' + pprint_diff(test_case.person_records, person_records))
            assert note_records == test_case.note_records, (test_name +
                ':\n' + pprint_diff(test_case.note_records, note_records))

    def test_parse_files(self):
        """Tests parsing of an XML file for each test case."""
        for test_name, test_case in TEST_CASES:
            if not test_case.do_parse_test:
                continue
            person_records, note_records = pfif.parse_file(
                StringIO.StringIO(test_case.xml))
            assert person_records == test_case.person_records, (test_name +
                ':\n' + pprint_diff(test_case.person_records, person_records))
            assert note_records == test_case.note_records, (test_name +
                ':\n' + pprint_diff(test_case.note_records, note_records))

    def test_write_file(self):
        """Tests writing of XML files for each test case."""
        for test_name, test_case in TEST_CASES:
            if not test_case.do_write_test:
                continue

            def get_notes_for_person(person): 
                return [
                    note for note in test_case.note_records
                    if note['person_record_id'] == person['person_record_id']
                ]

            file = StringIO.StringIO()
            pfif_version = pfif.PFIF_VERSIONS[test_case.pfif_version]

            # Start with fake entities so we can test entity-to-dict conversion.
            person_entities = map(dict_to_entity, test_case.person_records)

            # Convert to dicts and write the records.
            person_records = [
                pfif_version.person_to_dict(person, test_case.is_expired)
                for person in person_entities
            ]
            pfif_version.write_file(file, person_records, get_notes_for_person)
            assert file.getvalue() == test_case.xml, (
                test_name + ': ' + text_diff(test_case.xml, file.getvalue()))


if __name__ == '__main__':
    unittest.main()
