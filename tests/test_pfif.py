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
import unittest

# utility function duplicated here from server_tests.
# TODO(lschumacher): find a happy place to share this.
def pfif_diff(expected, actual):
    """Format expected != actual as a useful diff string."""
    return ''.join(difflib.context_diff(expected.splitlines(1),
                                        actual.splitlines(1)))

class PfifRecord(object):
    """object for constructing and correlating test data."""

    PREFIX = 'pfif'
    NAME  = 'pfif_name'
    pfif_records = []

    def __init__(self, version, data, person_records=[], note_records=[]):
        # we expect at most one person per record for this to work right.
        assert len(person_records) < 2
        self.version_ = version
        self.data_ = data
        self.expected_persons_ = person_records
        self.expected_notes_ = note_records
        PfifRecord.pfif_records.append(self)

    def get_data(self, prefix):
        pfif_prefix = ''
        pfif_name = ''
        if prefix:
            pfif_prefix = prefix + ':'
            pfif_name = ':' + prefix
        return self.data_ % { PfifRecord.PREFIX : pfif_prefix,
                              PfifRecord.NAME : pfif_name }

    def get_version(self):
        return self.version_

    def get_expected_persons(self):
        return self.expected_persons_

    def get_expected_notes(self):
        return self.expected_notes_

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
PFIF_1_3 = PfifRecord('1.3', '''\
<?xml version="1.0" encoding="UTF-8"?>
<%(pfif)spfif xmlns%(pfif_name)s="http://zesty.ca/pfif/1.3">
  <%(pfif)sperson>
    <%(pfif)sperson_record_id>test.google.com/person.21009</%(pfif)sperson_record_id>
    <%(pfif)sentry_date>2010-01-16T02:07:57Z</%(pfif)sentry_date>
    <%(pfif)sexpiry_date>2010-02-16T02:07:57Z</%(pfif)sexpiry_date>
    <%(pfif)sauthor_name>_test_author_name</%(pfif)sauthor_name>
    <%(pfif)sauthor_email>_test_author_email</%(pfif)sauthor_email>
    <%(pfif)sauthor_phone>_test_author_phone</%(pfif)sauthor_phone>
    <%(pfif)ssource_name>_test_source_name</%(pfif)ssource_name>
    <%(pfif)ssource_date>2000-01-01T00:00:00Z</%(pfif)ssource_date>
    <%(pfif)ssource_url>_test_source_url</%(pfif)ssource_url>
    <%(pfif)sfirst_name>_test_first_name</%(pfif)sfirst_name>
    <%(pfif)slast_name>_test_last_name</%(pfif)slast_name>
    <%(pfif)sfull_name>_test_first_name_dot_last_name</%(pfif)sfull_name>
    <%(pfif)ssex>female</%(pfif)ssex>
    <%(pfif)sdate_of_birth>1970-01-01</%(pfif)sdate_of_birth>
    <%(pfif)sage>35-45</%(pfif)sage>
    <%(pfif)shome_street>_test_home_street</%(pfif)shome_street>
    <%(pfif)shome_neighborhood>_test_home_neighborhood</%(pfif)shome_neighborhood>
    <%(pfif)shome_city>_test_home_city</%(pfif)shome_city>
    <%(pfif)shome_state>_test_home_state</%(pfif)shome_state>
    <%(pfif)shome_postal_code>_test_home_postal_code</%(pfif)shome_postal_code>
    <%(pfif)shome_country>US</%(pfif)shome_country>
    <%(pfif)sphoto_url>_test_photo_url</%(pfif)sphoto_url>
    <%(pfif)sother>description:
    _test_description &amp; &lt; &gt; "
</%(pfif)sother>
    <%(pfif)snote>
      <%(pfif)snote_record_id>test.google.com/note.27009</%(pfif)snote_record_id>
      <%(pfif)sperson_record_id>test.google.com/person.21009</%(pfif)sperson_record_id>
      <%(pfif)slinked_person_record_id>test.google.com/person.777</%(pfif)slinked_person_record_id>
      <%(pfif)sentry_date>2010-01-16T17:32:05Z</%(pfif)sentry_date>
      <%(pfif)sauthor_name>_test_author_name</%(pfif)sauthor_name>
      <%(pfif)sauthor_email>_test_author_email</%(pfif)sauthor_email>
      <%(pfif)sauthor_phone>_test_author_phone</%(pfif)sauthor_phone>
      <%(pfif)ssource_date>2000-02-02T02:02:02Z</%(pfif)ssource_date>
      <%(pfif)sfound>true</%(pfif)sfound>
      <%(pfif)sstatus>believed_alive</%(pfif)sstatus>
      <%(pfif)semail_of_found_person>_test_email_of_found_person</%(pfif)semail_of_found_person>
      <%(pfif)sphone_of_found_person>_test_phone_of_found_person</%(pfif)sphone_of_found_person>
      <%(pfif)slast_known_location>_test_last_known_location</%(pfif)slast_known_location>
      <%(pfif)stext>_test_text
    line two
</%(pfif)stext>
    </%(pfif)snote>
  </%(pfif)sperson>
</%(pfif)spfif>
''', [PERSON_RECORD_1_3], [NOTE_RECORD_1_3])

# A PFIF 1.3 XML document with prefixes on the tags, with the id coming before
# the note
PFIF_1_3_WITH_NOTE_BEFORE_ID = PfifRecord('1.3', '''\
<?xml version="1.0" encoding="UTF-8"?>
<%(pfif)spfif xmlns%(pfif_name)s="http://zesty.ca/pfif/1.3">
  <%(pfif)sperson>
    <%(pfif)sentry_date>2010-01-16T02:07:57Z</%(pfif)sentry_date>
    <%(pfif)sauthor_name>_test_author_name</%(pfif)sauthor_name>
    <%(pfif)sauthor_email>_test_author_email</%(pfif)sauthor_email>
    <%(pfif)sauthor_phone>_test_author_phone</%(pfif)sauthor_phone>
    <%(pfif)ssource_name>_test_source_name</%(pfif)ssource_name>
    <%(pfif)ssource_date>2000-01-01T00:00:00Z</%(pfif)ssource_date>
    <%(pfif)ssource_url>_test_source_url</%(pfif)ssource_url>
    <%(pfif)sfirst_name>_test_first_name</%(pfif)sfirst_name>
    <%(pfif)slast_name>_test_last_name</%(pfif)slast_name>
    <%(pfif)ssex>female</%(pfif)ssex>
    <%(pfif)sdate_of_birth>1970-01-01</%(pfif)sdate_of_birth>
    <%(pfif)sage>35-45</%(pfif)sage>
    <%(pfif)shome_street>_test_home_street</%(pfif)shome_street>
    <%(pfif)shome_neighborhood>_test_home_neighborhood</%(pfif)shome_neighborhood>
    <%(pfif)shome_city>_test_home_city</%(pfif)shome_city>
    <%(pfif)shome_state>_test_home_state</%(pfif)shome_state>
    <%(pfif)shome_postal_code>_test_home_postal_code</%(pfif)shome_postal_code>
    <%(pfif)shome_country>US</%(pfif)shome_country>
    <%(pfif)sphoto_url>_test_photo_url</%(pfif)sphoto_url>
    <%(pfif)sother>description:
    _test_description &amp; &lt; &gt; "
</%(pfif)sother>
    <%(pfif)snote>
      <%(pfif)snote_record_id>test.google.com/note.27009</%(pfif)snote_record_id>
      <%(pfif)sperson_record_id>test.google.com/person.21009</%(pfif)sperson_record_id>
      <%(pfif)slinked_person_record_id>test.google.com/person.777</%(pfif)slinked_person_record_id>
      <%(pfif)sentry_date>2010-01-16T17:32:05Z</%(pfif)sentry_date>
      <%(pfif)sauthor_name>_test_author_name</%(pfif)sauthor_name>
      <%(pfif)sauthor_email>_test_author_email</%(pfif)sauthor_email>
      <%(pfif)sauthor_phone>_test_author_phone</%(pfif)sauthor_phone>
      <%(pfif)ssource_date>2000-02-02T02:02:02Z</%(pfif)ssource_date>
      <%(pfif)sfound>true</%(pfif)sfound>
      <%(pfif)sstatus>believed_alive</%(pfif)sstatus>
      <%(pfif)semail_of_found_person>_test_email_of_found_person</%(pfif)semail_of_found_person>
      <%(pfif)sphone_of_found_person>_test_phone_of_found_person</%(pfif)sphone_of_found_person>
      <%(pfif)slast_known_location>_test_last_known_location</%(pfif)slast_known_location>
      <%(pfif)stext>_test_text
    line two
</%(pfif)stext>
    </%(pfif)snote>
    <%(pfif)sperson_record_id>test.google.com/person.21009</%(pfif)sperson_record_id>
  </%(pfif)sperson>
</%(pfif)spfif>
''',  [PERSON_RECORD_1_3], [NOTE_RECORD_1_3])

# A PFIF 1.3 XML document with notes only.
PFIF_WITH_NOTE_ONLY = PfifRecord('1.3', '''\
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
PFIF_1_2 = PfifRecord('1.2', '''\
<?xml version="1.0" encoding="UTF-8"?>
<%(pfif)spfif xmlns%(pfif_name)s="http://zesty.ca/pfif/1.2">
  <%(pfif)sperson>
    <%(pfif)sperson_record_id>test.google.com/person.21009</%(pfif)sperson_record_id>
    <%(pfif)sentry_date>2010-01-16T02:07:57Z</%(pfif)sentry_date>
    <%(pfif)sauthor_name>_test_author_name</%(pfif)sauthor_name>
    <%(pfif)sauthor_email>_test_author_email</%(pfif)sauthor_email>
    <%(pfif)sauthor_phone>_test_author_phone</%(pfif)sauthor_phone>
    <%(pfif)ssource_name>_test_source_name</%(pfif)ssource_name>
    <%(pfif)ssource_date>2000-01-01T00:00:00Z</%(pfif)ssource_date>
    <%(pfif)ssource_url>_test_source_url</%(pfif)ssource_url>
    <%(pfif)sfirst_name>_test_first_name</%(pfif)sfirst_name>
    <%(pfif)slast_name>_test_last_name</%(pfif)slast_name>
    <%(pfif)ssex>female</%(pfif)ssex>
    <%(pfif)sdate_of_birth>1970-01-01</%(pfif)sdate_of_birth>
    <%(pfif)sage>35-45</%(pfif)sage>
    <%(pfif)shome_street>_test_home_street</%(pfif)shome_street>
    <%(pfif)shome_neighborhood>_test_home_neighborhood</%(pfif)shome_neighborhood>
    <%(pfif)shome_city>_test_home_city</%(pfif)shome_city>
    <%(pfif)shome_state>_test_home_state</%(pfif)shome_state>
    <%(pfif)shome_postal_code>_test_home_postal_code</%(pfif)shome_postal_code>
    <%(pfif)shome_country>US</%(pfif)shome_country>
    <%(pfif)sphoto_url>_test_photo_url</%(pfif)sphoto_url>
    <%(pfif)sother>description:
    _test_description &amp; &lt; &gt; "
</%(pfif)sother>
    <%(pfif)snote>
      <%(pfif)snote_record_id>test.google.com/note.27009</%(pfif)snote_record_id>
      <%(pfif)sperson_record_id>test.google.com/person.21009</%(pfif)sperson_record_id>
      <%(pfif)slinked_person_record_id>test.google.com/person.777</%(pfif)slinked_person_record_id>
      <%(pfif)sentry_date>2010-01-16T17:32:05Z</%(pfif)sentry_date>
      <%(pfif)sauthor_name>_test_author_name</%(pfif)sauthor_name>
      <%(pfif)sauthor_email>_test_author_email</%(pfif)sauthor_email>
      <%(pfif)sauthor_phone>_test_author_phone</%(pfif)sauthor_phone>
      <%(pfif)ssource_date>2000-02-02T02:02:02Z</%(pfif)ssource_date>
      <%(pfif)sfound>true</%(pfif)sfound>
      <%(pfif)sstatus>believed_alive</%(pfif)sstatus>
      <%(pfif)semail_of_found_person>_test_email_of_found_person</%(pfif)semail_of_found_person>
      <%(pfif)sphone_of_found_person>_test_phone_of_found_person</%(pfif)sphone_of_found_person>
      <%(pfif)slast_known_location>_test_last_known_location</%(pfif)slast_known_location>
      <%(pfif)stext>_test_text
    line two
</%(pfif)stext>
    </%(pfif)snote>
  </%(pfif)sperson>
</%(pfif)spfif>
''', [PERSON_RECORD_1_2], [NOTE_RECORD_1_2])

# A PFIF 1.2 XML document with prefixes on the tags, with the id coming before
# the note
PFIF_1_2_WITH_NOTE_BEFORE_ID = PfifRecord('1.2', '''\
<?xml version="1.0" encoding="UTF-8"?>
<%(pfif)spfif xmlns%(pfif_name)s="http://zesty.ca/pfif/1.2">
  <%(pfif)sperson>
    <%(pfif)sentry_date>2010-01-16T02:07:57Z</%(pfif)sentry_date>
    <%(pfif)sauthor_name>_test_author_name</%(pfif)sauthor_name>
    <%(pfif)sauthor_email>_test_author_email</%(pfif)sauthor_email>
    <%(pfif)sauthor_phone>_test_author_phone</%(pfif)sauthor_phone>
    <%(pfif)ssource_name>_test_source_name</%(pfif)ssource_name>
    <%(pfif)ssource_date>2000-01-01T00:00:00Z</%(pfif)ssource_date>
    <%(pfif)ssource_url>_test_source_url</%(pfif)ssource_url>
    <%(pfif)sfirst_name>_test_first_name</%(pfif)sfirst_name>
    <%(pfif)slast_name>_test_last_name</%(pfif)slast_name>
    <%(pfif)ssex>female</%(pfif)ssex>
    <%(pfif)sdate_of_birth>1970-01-01</%(pfif)sdate_of_birth>
    <%(pfif)sage>35-45</%(pfif)sage>
    <%(pfif)shome_street>_test_home_street</%(pfif)shome_street>
    <%(pfif)shome_neighborhood>_test_home_neighborhood</%(pfif)shome_neighborhood>
    <%(pfif)shome_city>_test_home_city</%(pfif)shome_city>
    <%(pfif)shome_state>_test_home_state</%(pfif)shome_state>
    <%(pfif)shome_postal_code>_test_home_postal_code</%(pfif)shome_postal_code>
    <%(pfif)shome_country>US</%(pfif)shome_country>
    <%(pfif)sphoto_url>_test_photo_url</%(pfif)sphoto_url>
    <%(pfif)sother>description:
    _test_description &amp; &lt; &gt; "
</%(pfif)sother>
    <%(pfif)snote>
      <%(pfif)snote_record_id>test.google.com/note.27009</%(pfif)snote_record_id>
      <%(pfif)sperson_record_id>test.google.com/person.21009</%(pfif)sperson_record_id>
      <%(pfif)slinked_person_record_id>test.google.com/person.777</%(pfif)slinked_person_record_id>
      <%(pfif)sentry_date>2010-01-16T17:32:05Z</%(pfif)sentry_date>
      <%(pfif)sauthor_name>_test_author_name</%(pfif)sauthor_name>
      <%(pfif)sauthor_email>_test_author_email</%(pfif)sauthor_email>
      <%(pfif)sauthor_phone>_test_author_phone</%(pfif)sauthor_phone>
      <%(pfif)ssource_date>2000-02-02T02:02:02Z</%(pfif)ssource_date>
      <%(pfif)sfound>true</%(pfif)sfound>
      <%(pfif)sstatus>believed_alive</%(pfif)sstatus>
      <%(pfif)semail_of_found_person>_test_email_of_found_person</%(pfif)semail_of_found_person>
      <%(pfif)sphone_of_found_person>_test_phone_of_found_person</%(pfif)sphone_of_found_person>
      <%(pfif)slast_known_location>_test_last_known_location</%(pfif)slast_known_location>
      <%(pfif)stext>_test_text
    line two
</%(pfif)stext>
    </%(pfif)snote>
    <%(pfif)sperson_record_id>test.google.com/person.21009</%(pfif)sperson_record_id>
  </%(pfif)sperson>
</%(pfif)spfif>
''',  [PERSON_RECORD_1_2], [NOTE_RECORD_1_2])

# A PFIF 1.2 XML document with notes only.
PFIF_WITH_NOTE_ONLY = PfifRecord('1.2', '''\
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
PFIF_1_1 = PfifRecord('1.1', '''\
<?xml version="1.0" encoding="UTF-8"?>
<%(pfif)spfif xmlns%(pfif_name)s="http://zesty.ca/pfif/1.1">
  <%(pfif)sperson>
    <%(pfif)sperson_record_id>test.google.com/person.21009</%(pfif)sperson_record_id>
    <%(pfif)sentry_date>2010-01-16T02:07:57Z</%(pfif)sentry_date>
    <%(pfif)sauthor_name>_test_author_name</%(pfif)sauthor_name>
    <%(pfif)sauthor_email>_test_author_email</%(pfif)sauthor_email>
    <%(pfif)sauthor_phone>_test_author_phone</%(pfif)sauthor_phone>
    <%(pfif)ssource_name>_test_source_name</%(pfif)ssource_name>
    <%(pfif)ssource_date>2000-01-01T00:00:00Z</%(pfif)ssource_date>
    <%(pfif)ssource_url>_test_source_url</%(pfif)ssource_url>
    <%(pfif)sfirst_name>_test_first_name</%(pfif)sfirst_name>
    <%(pfif)slast_name>_test_last_name</%(pfif)slast_name>
    <%(pfif)shome_city>_test_home_city</%(pfif)shome_city>
    <%(pfif)shome_state>_test_home_state</%(pfif)shome_state>
    <%(pfif)shome_neighborhood>_test_home_neighborhood</%(pfif)shome_neighborhood>
    <%(pfif)shome_street>_test_home_street</%(pfif)shome_street>
    <%(pfif)shome_zip>_test_home_zip</%(pfif)shome_zip>
    <%(pfif)sphoto_url>_test_photo_url</%(pfif)sphoto_url>
    <%(pfif)sother>description:
    _test_description &amp; &lt; &gt; "
</%(pfif)sother>
    <%(pfif)snote>
      <%(pfif)snote_record_id>test.google.com/note.27009</%(pfif)snote_record_id>
      <%(pfif)sentry_date>2010-01-16T17:32:05Z</%(pfif)sentry_date>
      <%(pfif)sauthor_name>_test_author_name</%(pfif)sauthor_name>
      <%(pfif)sauthor_email>_test_author_email</%(pfif)sauthor_email>
      <%(pfif)sauthor_phone>_test_author_phone</%(pfif)sauthor_phone>
      <%(pfif)ssource_date>2000-02-02T02:02:02Z</%(pfif)ssource_date>
      <%(pfif)sfound>true</%(pfif)sfound>
      <%(pfif)semail_of_found_person>_test_email_of_found_person</%(pfif)semail_of_found_person>
      <%(pfif)sphone_of_found_person>_test_phone_of_found_person</%(pfif)sphone_of_found_person>
      <%(pfif)slast_known_location>_test_last_known_location</%(pfif)slast_known_location>
      <%(pfif)stext>_test_text
    line two
</%(pfif)stext>
    </%(pfif)snote>
  </%(pfif)sperson>
</%(pfif)spfif>
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
PFIF_WITH_NON_ASCII = PfifRecord('1.2', '''\
<?xml version="1.0" encoding="UTF-8"?>
<%(pfif)spfif xmlns%(pfif_name)s="http://zesty.ca/pfif/1.2">
  <%(pfif)sperson>
    <%(pfif)sperson_record_id>test.google.com/person.123</%(pfif)sperson_record_id>
    <%(pfif)sauthor_name>a with acute = \xc3\xa1</%(pfif)sauthor_name>
    <%(pfif)sauthor_email>c with cedilla = \xc3\xa7</%(pfif)sauthor_email>
    <%(pfif)sauthor_phone>e with acute = \xc3\xa9</%(pfif)sauthor_phone>
    <%(pfif)sfirst_name>greek alpha = \xce\xb1</%(pfif)sfirst_name>
    <%(pfif)slast_name>hebrew alef = \xd7\x90</%(pfif)slast_name>
  </%(pfif)sperson>
</%(pfif)spfif>
''', [PERSON_RECORD_WITH_NON_ASCII], [])

class PfifTests(unittest.TestCase):
    def check_pfif_with_prefix(self, pfif_record, prefix):
        person_records, note_records = pfif.parse(pfif_record.get_data(prefix))
        assert len(person_records) == len(pfif_record.get_expected_persons())
        for p,e in zip(person_records, pfif_record.get_expected_persons()):
            assert e == p #, pfif_diff(e, p)
        assert len(note_records) == len(pfif_record.get_expected_notes())
        for n, e in zip(note_records, pfif_record.get_expected_notes()):
            assert e == n # , pfif_diff(e, n)

    def test_pfif_records(self):
        """Iterator over all the data and test with and without prefixes."""
        for pfif_record in PfifRecord.pfif_records:
            self.check_pfif_with_prefix(pfif_record, '')
            self.check_pfif_with_prefix(pfif_record, 'pfif')

    def test_parse_file(self):
        file = StringIO.StringIO(PFIF_1_2.get_data('pfif'))
        person_records, note_records = pfif.parse_file(file)
        assert PFIF_1_2.get_expected_persons() == person_records
        assert PFIF_1_2.get_expected_notes() == note_records

    def test_write_file(self):
        pfif_record = PFIF_1_2
        person_record = pfif_record.get_expected_persons()[0]
        def expected_notes(person): 
            assert person['person_record_id'] == person_record['person_record_id']
            return person_record.get_expected_notes()
        file = StringIO.StringIO()
        pfif.PFIF_1_2.write_file(file, [person_record], expected_notes)
        expected_value = PFIF_1_2.get_data('pfif')
        file_value = file.getvalue()
        assert expected_value == file_value, \
            pfif_diff(expected_value, file_value)

    def test_write_file_1_1(self):
        file = StringIO.StringIO()
        pfif.PFIF_1_1.write_file(
            file, [PERSON_RECORD_1_1], get_notes_for_person, PfifRecord.get_expected_notes)
        expected_value = PFIF_1_1.get_data('pfif')
        file_value = file.getvalue()
        assert expected_value == file_value, \
            pfif_diff(expected_value, file_value)

    def test_write_file_with_non_ascii(self):
        file = StringIO.StringIO()
        pfif.PFIF_1_2.write_file(file, [PERSON_RECORD_WITH_NON_ASCII])
        file_value = file.getvalue()
        person_value =  PFIF_WITH_NON_ASCII.get_data('pfif')
        assert person_value == file_value, \
            pfif_diff(person_value, file_value)


if __name__ == '__main__':
    unittest.main()
