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

__author__ = 'kpy@google.com (Ka-Ping Yee) and many other Googlers'

import StringIO
import pfif
import unittest

# A PFIF 1.2 XML document with prefixes on the tags.
PFIF_WITH_PREFIXES = '''\
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
'''

# A PFIF 1.2 XML document with prefixes on the tags, with the id coming before
# the note
PFIF_WITH_NOTE_BEFORE_ID = '''\
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
'''

# A PFIF 1.2 XML document without tag prefixes (using a default namespace).
PFIF_WITHOUT_PREFIXES = '''\
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
'''

# A PFIF 1.2 XML document with notes only.
PFIF_WITH_NOTE_ONLY = '''\
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
'''

# The expected parsed records corresponding to all of the above.
PERSON_RECORD = {
    'person_record_id': 'test.google.com/person.21009',
    'entry_date': '2010-01-16T02:07:57Z',
    'author_name': '_test_author_name',
    'author_email': '_test_author_email',
    'author_phone': '_test_author_phone',
    'source_name': '_test_source_name',
    'source_date': '2000-01-01T00:00:00Z',
    'source_url': '_test_source_url',
    'first_name': '_test_first_name',
    'last_name': '_test_last_name',
    'sex': 'female',
    'date_of_birth': '1970-01-01',
    'age': '35-45',
    'home_street': '_test_home_street',
    'home_neighborhood': '_test_home_neighborhood',
    'home_city': '_test_home_city',
    'home_state': '_test_home_state',
    'home_postal_code': '_test_home_postal_code',
    'home_country': 'US',
    'photo_url': '_test_photo_url',
    'other': 'description:\n    _test_description & < > "\n',
}

NOTE_RECORD = {
    'note_record_id': 'test.google.com/note.27009',
    'person_record_id': 'test.google.com/person.21009',
    'linked_person_record_id': 'test.google.com/person.777',
    'entry_date': '2010-01-16T17:32:05Z',
    'author_name': '_test_author_name',
    'author_email': '_test_author_email',
    'author_phone': '_test_author_phone',
    'source_date': '2000-02-02T02:02:02Z',
    'found': 'true',
    'status': 'believed_alive',
    'email_of_found_person': '_test_email_of_found_person',
    'phone_of_found_person': '_test_phone_of_found_person',
    'last_known_location': '_test_last_known_location',
    'text': '_test_text\n    line two\n',
}

# A PFIF 1.1 XML document with tag prefixes.
PFIF_1_1_WITH_PREFIXES = '''\
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
'''

# The expected parsed records corresponding to both of the above.
PERSON_RECORD_1_1 = {
    'person_record_id': 'test.google.com/person.21009',
    'entry_date': '2010-01-16T02:07:57Z',
    'author_name': '_test_author_name',
    'author_email': '_test_author_email',
    'author_phone': '_test_author_phone',
    'source_name': '_test_source_name',
    'source_date': '2000-01-01T00:00:00Z',
    'source_url': '_test_source_url',
    'first_name': '_test_first_name',
    'last_name': '_test_last_name',
    'home_street': '_test_home_street',
    'home_neighborhood': '_test_home_neighborhood',
    'home_city': '_test_home_city',
    'home_state': '_test_home_state',
    'home_zip': '_test_home_zip',
    'photo_url': '_test_photo_url',
    'other': 'description:\n    _test_description & < > "\n',
}

NOTE_RECORD_1_1 = {
    'note_record_id': 'test.google.com/note.27009',
    'person_record_id': 'test.google.com/person.21009',
    'entry_date': '2010-01-16T17:32:05Z',
    'author_name': '_test_author_name',
    'author_email': '_test_author_email',
    'author_phone': '_test_author_phone',
    'source_date': '2000-02-02T02:02:02Z',
    'found': 'true',
    'email_of_found_person': '_test_email_of_found_person',
    'phone_of_found_person': '_test_phone_of_found_person',
    'last_known_location': '_test_last_known_location',
    'text': '_test_text\n    line two\n',
}

# A PFIF document containing some accented characters in UTF-8 encoding.
PFIF_WITH_NON_ASCII = '''\
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
'''

# The expected parsed record corresponding to the above.
PERSON_RECORD_WITH_NON_ASCII = {
    'person_record_id': 'test.google.com/person.123',
    'author_name': u'a with acute = \u00e1',
    'author_email': u'c with cedilla = \u00e7',
    'author_phone': u'e with acute = \u00e9',
    'first_name': u'greek alpha = \u03b1',
    'last_name': u'hebrew alef = \u05d0'
}

class PfifTests(unittest.TestCase):
    def test_parse(self):
        person_records, note_records = pfif.parse(PFIF_WITH_PREFIXES)
        assert [PERSON_RECORD] == person_records
        assert [NOTE_RECORD] == note_records

    def test_parse_note_only(self):
        person_records, note_records = pfif.parse(PFIF_WITH_NOTE_ONLY)
        assert [] == person_records
        assert [NOTE_RECORD] == note_records

    def test_parse_1_1(self):
        person_records, note_records = pfif.parse(PFIF_1_1_WITH_PREFIXES)
        assert [PERSON_RECORD_1_1] == person_records
        assert [NOTE_RECORD_1_1] == note_records

    def test_parse_note_before_id(self):
        person_records, note_records = pfif.parse(PFIF_WITH_NOTE_BEFORE_ID)
        assert [PERSON_RECORD] == person_records
        assert [NOTE_RECORD] == note_records

    def test_parse_without_prefixes(self):
        person_records, note_records = pfif.parse(PFIF_WITHOUT_PREFIXES)
        assert [PERSON_RECORD] == person_records
        assert [NOTE_RECORD] == note_records

    def test_parse_with_non_ascii(self):
        person_records, note_records = pfif.parse(PFIF_WITH_NON_ASCII)
        assert [PERSON_RECORD_WITH_NON_ASCII] == person_records
        assert [] == note_records

    def test_parse_file(self):
        file = StringIO.StringIO(PFIF_WITH_PREFIXES)
        person_records, note_records = pfif.parse_file(file)
        assert [PERSON_RECORD] == person_records
        assert [NOTE_RECORD] == note_records

    def test_write_file(self):
        def get_notes_for_person(person):
            assert person['person_record_id'] == 'test.google.com/person.21009'
            return [NOTE_RECORD]

        file = StringIO.StringIO()
        pfif.PFIF_1_2.write_file(file, [PERSON_RECORD], get_notes_for_person)
        assert PFIF_WITH_PREFIXES == file.getvalue()

    def test_write_file_1_1(self):
        def get_notes_for_person(person):
            assert person['person_record_id'] == 'test.google.com/person.21009'
            return [NOTE_RECORD_1_1]

        file = StringIO.StringIO()
        pfif.PFIF_1_1.write_file(
            file, [PERSON_RECORD_1_1], get_notes_for_person)
        assert PFIF_1_1_WITH_PREFIXES == file.getvalue()

    def test_write_file_with_non_ascii(self):
        file = StringIO.StringIO()
        pfif.PFIF_1_2.write_file(file, [PERSON_RECORD_WITH_NON_ASCII])
        assert PFIF_WITH_NON_ASCII == file.getvalue()

if __name__ == '__main__':
    unittest.main()
