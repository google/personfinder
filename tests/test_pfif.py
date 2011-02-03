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
import pfif
import sys
import unittest

# utility function duplicated here from server_tests.
# TODO(lschumacher): find a happy place to share this.
def strdiff(expected, actual):
    """Format expected != actual as a useful diff string."""
    return ''.join(difflib.context_diff(expected, actual))

class PfifRecord(object):
    """object for constructing and correlating test data with expected results.

    We keep a list of all the PfifRecords constructed, and the tests just 
    iterate over them and validate results.  Testing changes to the pfif format
    should just require adding new objects of this type and the read/write/parse
    tests will be executed automatically.
    """

    pfif_records = []

    def __init__(self, version, name, data, person_records=[], note_records=[],
                 write_test=True):
        # we expect at most one person per record for this to work correctly.
        assert len(person_records) < 2
        self.name = name
        self.version = version
        self.write_test = write_test
        self.data = data
        self.expected_persons = person_records
        self.expected_notes = note_records
        PfifRecord.pfif_records.append(self)


# The expected parsed records corresponding to the xml docs below.
PERSON_RECORD_1_3 = {
    'person_record_id': 'test.google.com/person.21009',
    'entry_date': '2010-01-16T02:07:57Z',
    'expiry_date': '2010-02-16T02:07:57Z',
    'author_name': '_test_author_name',
    'author_email': '_test_author_email',
    'author_phone': '_test_author_phone',
    'source_name': '_test_source_name',
    'source_date': '2000-01-01T00:00:00Z',
    'source_url': '_test_source_url',
    'first_name': '_test_first_name',
    'last_name': '_test_last_name',
    'full_name': '_test_first_name_dot_last_name',
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

NOTE_RECORD_1_3 = {
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


# A PFIF 1.3 XML document with prefixes on the tags.
PFIF_1_3 = PfifRecord('1.3', 'pfif 1.3', '''\
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
''', [PERSON_RECORD_1_3], [NOTE_RECORD_1_3])

# A PFIF 1.3 XML document with prefixes on the tags, with the id coming before
# the note.  Doesn't work in the write tests because of the id coming out of order.
PFIF_1_3_WITH_NOTE_BEFORE_ID = PfifRecord('1.3', '1.3 note before id', '''\
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
''',  [PERSON_RECORD_1_3], [NOTE_RECORD_1_3], False)

# A PFIF 1.3 XML document with notes only.
PFIF_WITH_NOTE_ONLY = PfifRecord('1.3', 'pfif 1.3 note only', '''\
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
''', [], [NOTE_RECORD_1_3])


# The expected parsed records corresponding to the 1.2 xml docs below.
PERSON_RECORD_1_2 = {
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

NOTE_RECORD_1_2 = {
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


# A PFIF 1.2 XML document with prefixes on the tags.
PFIF_1_2 = PfifRecord('1.2', 'pfif 1.2', '''\
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
''', [PERSON_RECORD_1_2], [NOTE_RECORD_1_2])

# A PFIF 1.2 XML document without prefixes on the tags.
PFIF_1_2_NOPREFIX = PfifRecord('1.2', 'pfif 1.2 no prefix', '''\
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
''', [PERSON_RECORD_1_2], [NOTE_RECORD_1_2], False)


# A PFIF 1.2 XML document with prefixes on the tags, with the id coming before
# the note.  Not usable in write tests.
PFIF_1_2_WITH_NOTE_BEFORE_ID = PfifRecord('1.2', 'pfif 1.2 note before id', '''\
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
''',  [PERSON_RECORD_1_2], [NOTE_RECORD_1_2], False)

# A PFIF 1.2 XML document with notes only.
PFIF_WITH_NOTE_ONLY = PfifRecord('1.2', 'pfif 1.2, note only',  '''\
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
''', [], [NOTE_RECORD_1_2])

# The expected parsed records corresponding to 1_1 records below.
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

# A PFIF 1.1 XML document with tag prefixes.
PFIF_1_1 = PfifRecord('1.1', 'pfif 1.1', '''\
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
''', [PERSON_RECORD_1_1], [NOTE_RECORD_1_1])

# The expected parsed record corresponding to the next one.
PERSON_RECORD_WITH_NON_ASCII = {
    'person_record_id': 'test.google.com/person.123',
    'author_name': u'a with acute = \u00e1',
    'author_email': u'c with cedilla = \u00e7',
    'author_phone': u'e with acute = \u00e9',
    'first_name': u'greek alpha = \u03b1',
    'last_name': u'hebrew alef = \u05d0'
}

# A PFIF document containing some accented characters in UTF-8 encoding.
PFIF_WITH_NON_ASCII = PfifRecord('1.2', 'pfif with non ascii', '''\
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
''', [PERSON_RECORD_WITH_NON_ASCII], [])

class PfifTests(unittest.TestCase):
    """Iterates over the PfifRecords and verifies read/write/parse works."""

    def test_pfif_records(self):
        """Iterate over all the data and test with and without prefixes."""
        for pfif_record in PfifRecord.pfif_records:
            person_records, note_records = pfif.parse(pfif_record.data)
            assert len(person_records) == len(pfif_record.expected_persons)
            for p, e in zip(person_records, pfif_record.expected_persons):
                assert  e == p, '%s failed: %s' % (
                    pfif_record.name, 
                    # this isn't as pretty as one might hope.
                    strdiff(str(e).replace(',','\n,').split(','),
                            str(p).replace(',','\n,').split(',')))
            assert len(note_records) == len(pfif_record.expected_notes)
            for n, e in zip(note_records, pfif_record.expected_notes):
                assert e == n, strdiff(e, n)


    def test_parse_files(self):
        for record in PfifRecord.pfif_records:
            file = StringIO.StringIO(record.data)
            person_records, note_records = pfif.parse_file(file)
            assert record.expected_persons == person_records
            assert record.expected_notes == note_records

    def test_write_file(self):
        for record in PfifRecord.pfif_records:
            if not record.expected_persons or not record.write_test:
                continue
            person_record = record.expected_persons[0]
            def expected_notes(person): 
                assert person['person_record_id'] == person_record[
                    'person_record_id']
                return record.expected_notes
            file = StringIO.StringIO()
            pfif_version = pfif.PFIF_VERSIONS[record.version]
            pfif_version.write_file(file, [person_record], expected_notes)
            expected_value = record.data
            file_value = file.getvalue()
            assert expected_value == file_value, \
                '%s failed, diff=%s' % (
                record.name, 
                strdiff(expected_value.splitlines(1), file_value.splitlines(1)))


if __name__ == '__main__':
    unittest.main()
