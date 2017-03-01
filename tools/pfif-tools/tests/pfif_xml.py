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

"""PFIF XML for use with tests."""

XML_INVALID = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>"""

XML_11_SMALL = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:person />
</pfif:pfif>"""

XML_11_FULL = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:person>
    <pfif:person_record_id>example.org/local-id.3</pfif:person_record_id>
    <pfif:entry_date>1234-56-78T90:12:34Z</pfif:entry_date>
    <pfif:author_name>author name</pfif:author_name>
    <pfif:author_email>email@example.org</pfif:author_email>
    <pfif:author_phone>+12345678901</pfif:author_phone>
    <pfif:source_name>source name</pfif:source_name>
    <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
    <pfif:source_url>http://source.u.r/l</pfif:source_url>
    <pfif:first_name>FIRST NAME</pfif:first_name>
    <pfif:last_name>LAST NAME</pfif:last_name>
    <pfif:home_city>HOME CITY</pfif:home_city>
    <pfif:home_state>CA</pfif:home_state>
    <pfif:home_neighborhood>HOME NEIGHBORHOOD</pfif:home_neighborhood>
    <pfif:home_street>HOME STREET</pfif:home_street>
    <pfif:home_zip>12345</pfif:home_zip>
    <pfif:photo_url>https://user:pass@host:999/url_path?var=val#hash</pfif:photo_url>
    <pfif:other>other text</pfif:other>
    <pfif:note>
      <pfif:note_record_id>www.example.org/local-id.4</pfif:note_record_id>
      <pfif:entry_date>1234-56-78T90:12:34Z</pfif:entry_date>
      <pfif:author_name>author name</pfif:author_name>
      <pfif:author_email>author-email@exmaple.org</pfif:author_email>
      <pfif:author_phone>123.456.7890</pfif:author_phone>
      <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
      <pfif:found>true</pfif:found>
      <pfif:email_of_found_person>email@example.org</pfif:email_of_found_person>
      <pfif:phone_of_found_person>(123)456-7890</pfif:phone_of_found_person>
      <pfif:last_known_location>last known location</pfif:last_known_location>
      <pfif:text>large text string</pfif:text>
    </pfif:note>
    <pfif:note>
      <pfif:note_record_id>www.example.org/local-id.5</pfif:note_record_id>
      <pfif:author_name>author name</pfif:author_name>
      <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
      <pfif:found>false</pfif:found>
      <pfif:text>large text string</pfif:text>
    </pfif:note>
  </pfif:person>
</pfif:pfif>"""

XML_NON_PFIF_ROOT = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:html xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person />
</pfif:html>"""

XML_NO_NAMESPACE = """<?xml version="1.0" encoding="UTF-8"?>
<pfif>
  <person />
</pfif>"""

XML_BAD_PFIF_VERSION = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/9.9">
  <pfif:person />
</pfif:pfif>"""

XML_BAD_PFIF_WEBSITE = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.com/pfif/1.2">
  <pfif:person />
</pfif:pfif>"""

XML_ROOT_LACKS_CHILD = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2" />"""

XML_ROOT_HAS_BAD_CHILD = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:notAPersonOrNote />
</pfif:pfif>"""

XML_TOP_LEVEL_NOTE_11 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:note />
</pfif:pfif>"""

XML_TOP_LEVEL_NOTE_12 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:note />
</pfif:pfif>"""

XML_NOTES_WITH_CHILDREN = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:note>
    <pfif:person_record_id />
    <pfif:note_record_id />
    <pfif:author_name />
    <pfif:source_date />
    <pfif:text />
  </pfif:note>
  <pfif:person>
    <pfif:note>
      <pfif:note_record_id />
      <pfif:author_name />
      <pfif:source_date />
      <pfif:text />
    </pfif:note>
  </pfif:person>
</pfif:pfif>"""

XML_NOTES_NO_CHILDREN = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:note />
  <pfif:person>
    <pfif:note />
  </pfif:person>
</pfif:pfif>"""

XML_PERSON_WITH_CHILDREN_11 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:person>
    <pfif:person_record_id />
    <pfif:first_name />
    <pfif:last_name />
  </pfif:person>
</pfif:pfif>"""

XML_PERSON_WITH_CHILDREN_13 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id />
    <pfif:source_date />
    <pfif:full_name />
  </pfif:person>
</pfif:pfif>"""

XML_PERSON_NO_CHILDREN_13 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person />
</pfif:pfif>"""

XML_INCORRECT_FORMAT_11 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:person>
    <pfif:person_record_id>example.org/</pfif:person_record_id>
    <pfif:entry_date>123456-78T90:12:34Z</pfif:entry_date>
    <pfif:author_email>@example.org</pfif:author_email>
    <pfif:author_phone>123defghi</pfif:author_phone>
    <pfif:source_date>1234-56-7890:12:34Z</pfif:source_date>
    <pfif:source_url>!.%^*</pfif:source_url>
    <pfif:first_name>lowercase first name</pfif:first_name>
    <pfif:last_name>LOWEr</pfif:last_name>
    <pfif:home_city>lOWER</pfif:home_city>
    <pfif:home_state>LONG</pfif:home_state>
    <pfif:home_neighborhood>lower</pfif:home_neighborhood>
    <pfif:home_street>loWer</pfif:home_street>
    <pfif:home_zip>NOT NUMERIC</pfif:home_zip>
    <pfif:photo_url>bad.port:foo</pfif:photo_url>
    <pfif:note>
      <pfif:note_record_id>/local-id.4</pfif:note_record_id>
      <pfif:entry_date>1234-56-78T90:12:34</pfif:entry_date>
      <pfif:author_email>author-email</pfif:author_email>
      <pfif:author_phone>abc-def-ghij</pfif:author_phone>
      <pfif:source_date>123a-56-78T90:12:34Z</pfif:source_date>
      <pfif:found>not-true-or-false</pfif:found>
      <pfif:email_of_found_person>email@</pfif:email_of_found_person>
      <pfif:phone_of_found_person>abc1234567</pfif:phone_of_found_person>
    </pfif:note>
    <pfif:note>
      <pfif:note_record_id>http://foo/bar</pfif:note_record_id>
    </pfif:note>
  </pfif:person>
</pfif:pfif>"""

XML_FULL_12 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:sex>male</pfif:sex>
    <pfif:date_of_birth>1990-09-15</pfif:date_of_birth>
    <pfif:age>20</pfif:age>
    <pfif:home_country>US</pfif:home_country>
    <pfif:home_state>OR</pfif:home_state>
    <pfif:home_postal_code>94309</pfif:home_postal_code>
    <pfif:first_name>lowercase first</pfif:first_name>
    <pfif:last_name>lower last</pfif:last_name>
    <pfif:home_city>lower city</pfif:home_city>
    <pfif:home_neighborhood>lower neighborhood</pfif:home_neighborhood>
    <pfif:home_street>lower street</pfif:home_street>
    <pfif:note>
      <pfif:status>information_sought</pfif:status>
    </pfif:note>
  </pfif:person>
  <pfif:person>
    <pfif:sex>female</pfif:sex>
    <pfif:home_street>street address</pfif:home_street>
    <pfif:date_of_birth>1990-09</pfif:date_of_birth>
    <pfif:age>3-100</pfif:age>
    <pfif:home_state>71</pfif:home_state>
    <pfif:note>
      <pfif:status>believed_alive</pfif:status>
    </pfif:note>
  </pfif:person>
  <pfif:person>
    <pfif:sex>other</pfif:sex>
    <pfif:date_of_birth>1990</pfif:date_of_birth>
    <pfif:home_state>ABC</pfif:home_state>
    <pfif:note>
      <pfif:status>believed_dead</pfif:status>
    </pfif:note>
  </pfif:person>
  <pfif:note>
    <pfif:person_record_id>example.org/local1</pfif:person_record_id>
    <pfif:linked_person_record_id>example.org/id2</pfif:linked_person_record_id>
    <pfif:status>is_note_author</pfif:status>
  </pfif:note>
  <pfif:note>
    <pfif:status>believed_missing</pfif:status>
  </pfif:note>
</pfif:pfif>"""

XML_INCORRECT_FORMAT_12 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:sex>not-male-or-female-or-other</pfif:sex>
    <pfif:date_of_birth>09-15-1990</pfif:date_of_birth>
    <pfif:age>20.5</pfif:age>
    <pfif:home_country>abc</pfif:home_country>
    <pfif:home_state>1234</pfif:home_state>
    <pfif:home_postal_code>foo</pfif:home_postal_code>
    <pfif:note>
      <pfif:status>weird_belief</pfif:status>
    </pfif:note>
  </pfif:person>
  <pfif:person>
    <pfif:date_of_birth>September 15, 1990</pfif:date_of_birth>
    <pfif:age>3,100</pfif:age>
  </pfif:person>
  <pfif:person>
    <pfif:date_of_birth>1900-ab</pfif:date_of_birth>
  </pfif:person>
  <pfif:note>
    <pfif:person_record_id>example.org</pfif:person_record_id>
    <pfif:linked_person_record_id>/id2</pfif:linked_person_record_id>
  </pfif:note>
</pfif:pfif>"""

XML_CORRECT_FORMAT_13 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:full_name>john doe</pfif:full_name>
    <pfif:expiry_date>1234-56-78T90:12:34Z</pfif:expiry_date>
  </pfif:person>
</pfif:pfif>"""

XML_INCORRECT_FORMAT_13 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:expiry_date>12a4-56-78T90:12:34Z</pfif:expiry_date>
  </pfif:person>
</pfif:pfif>"""

XML_UNIQUE_PERSON_IDS = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/1</pfif:person_record_id>
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id>example.org/2</pfif:person_record_id>
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id>example.com/1</pfif:person_record_id>
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id>example.com/2</pfif:person_record_id>
  </pfif:person>
</pfif:pfif>"""

XML_UNIQUE_NOTE_IDS = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:note>
    <pfif:note_record_id>example.org/1</pfif:note_record_id>
  </pfif:note>
  <pfif:note>
    <pfif:note_record_id>example.org/2</pfif:note_record_id>
  </pfif:note>
  <pfif:note>
    <pfif:note_record_id>example.com/1</pfif:note_record_id>
  </pfif:note>
  <pfif:note>
    <pfif:note_record_id>example.com/2</pfif:note_record_id>
  </pfif:note>
</pfif:pfif>"""

XML_DUPLICATE_PERSON_IDS = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/1</pfif:person_record_id>
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id>example.org/1</pfif:person_record_id>
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id>example.com/2</pfif:person_record_id>
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id>example.com/2</pfif:person_record_id>
  </pfif:person>
</pfif:pfif>"""

XML_DUPLICATE_NOTE_IDS = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:note>
    <pfif:note_record_id>example.org/1</pfif:note_record_id>
  </pfif:note>
  <pfif:person>
    <pfif:note>
      <pfif:note_record_id>example.org/1</pfif:note_record_id>
    </pfif:note>
  </pfif:person>
  <pfif:note>
    <pfif:note_record_id>example.com/1</pfif:note_record_id>
  </pfif:note>
  <pfif:note>
    <pfif:note_record_id>example.com/1</pfif:note_record_id>
  </pfif:note>
</pfif:pfif>"""

XML_DUPLICATE_PERSON_AND_NOTE_ID = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/1</pfif:person_record_id>
  </pfif:person>
  <pfif:note>
    <pfif:note_record_id>example.org/1</pfif:note_record_id>
  </pfif:note>
</pfif:pfif>"""

XML_NOTES_BELONG_TO_PEOPLE = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:note>
    <pfif:person_record_id>example.org/1</pfif:person_record_id>
  </pfif:note>
  <pfif:person>
    <pfif:person_record_id>example.org/1</pfif:person_record_id>
    <pfif:note>
      <pfif:person_record_id>example.org/1</pfif:person_record_id>
    </pfif:note>
    <pfif:note />
  </pfif:person>
</pfif:pfif>"""

XML_NOTES_WITHOUT_PEOPLE = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:note />
  <pfif:person>
    <pfif:person_record_id>example.org/1</pfif:person_record_id>
    <pfif:note>
      <pfif:person_record_id>example.org/2</pfif:person_record_id>
    </pfif:note>
  </pfif:person>
</pfif:pfif>"""

XML_MISSING_FIELDS_11 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:person>
    <pfif:person_record_id>example.org/1</pfif:person_record_id>
    <pfif:other>other</pfif:other>
    <pfif:note>
      <pfif:note_record_id>example.org/2</pfif:note_record_id>
      <pfif:text>text</pfif:text>
    </pfif:note>
  </pfif:person>
</pfif:pfif>"""

XML_INCORRECT_FIELD_ORDER_11 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:person>
    <pfif:person_record_id />
    <pfif:note>
      <pfif:note_record_id />
      <pfif:text />
      <pfif:found />
    </pfif:note>
    <pfif:other />
  </pfif:person>
  <pfif:person>
    <pfif:note>
      <pfif:text />
      <pfif:note_record_id />
    </pfif:note>
    <pfif:person_record_id />
  </pfif:person>
  <pfif:person>
    <pfif:home_state />
    <pfif:home_city />
  </pfif:person>
</pfif:pfif>"""

XML_EXTRANEOUS_FIELD_11 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:person>
    <pfif:person_record_id>example.org/person</pfif:person_record_id>
    <pfif:foo />
    <pfif:other />
  </pfif:person>
</pfif:pfif>"""

XML_EXTRANEOUS_FIELD_11_MAP = {
    'example.org/person' : {'person_record_id' : 'example.org/person',
                            'foo' : '',
                            'other' : ''}}

XML_CORRECT_FIELD_ORDER_12 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id />
    <pfif:other />
    <pfif:home_state />
    <pfif:home_city />
    <pfif:note>
      <pfif:note_record_id />
      <pfif:text />
      <pfif:found />
    </pfif:note>
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id />
    <pfif:note>
      <pfif:note_record_id />
      <pfif:found />
      <pfif:source_date />
    </pfif:note>
    <pfif:note />
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id />
    <pfif:home_state />
    <pfif:home_city />
  </pfif:person>
  <pfif:note>
    <pfif:note_record_id />
    <pfif:person_record_id />
    <pfif:text />
    <pfif:author_name />
  </pfif:note>
</pfif:pfif>"""

XML_INCORRECT_PERSON_FIELD_ORDER_12 = """<?xml version="1.0"
  encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id />
    <pfif:note />
    <pfif:home_city />
  </pfif:person>
  <pfif:person>
    <pfif:home_city />
    <pfif:person_record_id />
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id />
    <pfif:note />
    <pfif:home_city />
    <pfif:note />
  </pfif:person>
</pfif:pfif>"""

XML_INCORRECT_NOTE_FIELD_ORDER_12 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:note>
    <pfif:note_record_id />
    <pfif:text />
    <pfif:person_record_id />
  </pfif:note>
  <pfif:note>
    <pfif:text />
    <pfif:note_record_id />
    <pfif:person_record_id />
  </pfif:note>
  <pfif:note>
    <pfif:text />
    <pfif:note_record_id />
  </pfif:note>
  <pfif:note>
    <pfif:text />
    <pfif:person_record_id />
  </pfif:note>
</pfif:pfif>"""

XML_ODD_ORDER_13 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id />
    <pfif:note>
      <pfif:note_record_id />
      <pfif:text />
      <pfif:found />
    </pfif:note>
    <pfif:other />
  </pfif:person>
  <pfif:person>
    <pfif:note>
      <pfif:text />
      <pfif:note_record_id />
    </pfif:note>
    <pfif:person_record_id />
  </pfif:person>
  <pfif:person>
    <pfif:home_state />
    <pfif:home_city />
  </pfif:person>
</pfif:pfif>"""

XML_EXPIRE_99_HAS_DATA_NONSYNCED_DATES = """<?xml version="1.0"
  encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/id</pfif:person_record_id>
    <pfif:source_date>1997-02-03T04:05:06Z</pfif:source_date>
    <pfif:entry_date>1998-02-03T04:05:06Z</pfif:entry_date>
    <pfif:expiry_date>1999-02-03T04:05:06Z</pfif:expiry_date>
    <pfif:note>
      <pfif:note_record_id>not/deleted</pfif:note_record_id>
    </pfif:note>
    <pfif:other>not deleted or omitted</pfif:other>
  </pfif:person>
  <pfif:note>
    <pfif:person_record_id>example.org/id</pfif:person_record_id>
    <pfif:text>this isn't deleted either</pfif:text>
  </pfif:note>
</pfif:pfif>"""

XML_EXPIRE_99_EMPTY_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/id</pfif:person_record_id>
    <pfif:source_date>1999-02-03T04:05:06Z</pfif:source_date>
    <pfif:entry_date>1999-02-03T04:05:06Z</pfif:entry_date>
    <pfif:expiry_date>1999-02-03T04:05:06Z</pfif:expiry_date>
    <pfif:note>
      <pfif:note_record_id></pfif:note_record_id>
    </pfif:note>
    <pfif:other></pfif:other>
  </pfif:person>
</pfif:pfif>"""

XML_EXPIRE_99_NO_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/id</pfif:person_record_id>
    <pfif:expiry_date>1999-02-03T04:05:06Z</pfif:expiry_date>
    <pfif:source_date>1999-02-03T04:05:06Z</pfif:source_date>
    <pfif:entry_date>1999-02-03T04:05:06Z</pfif:entry_date>
  </pfif:person>
</pfif:pfif>"""

XML_EXPIRE_99_HAS_NOTE_SYNCED_DATES = """<?xml version="1.0"
  encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/id1</pfif:person_record_id>
    <pfif:expiry_date>1999-02-03T04:05:06Z</pfif:expiry_date>
    <pfif:source_date>1999-02-03T04:05:06Z</pfif:source_date>
    <pfif:entry_date>1999-02-03T04:05:06Z</pfif:entry_date>
    <pfif:note>
      <pfif:note_record_id>not/deleted</pfif:note_record_id>
    </pfif:note>
  </pfif:person>
</pfif:pfif>"""

XML_EXPIRE_99_HAS_DATA_SYNCED_DATES = """<?xml version="1.0"
  encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/id1</pfif:person_record_id>
    <pfif:expiry_date>1999-02-03T04:05:06Z</pfif:expiry_date>
    <pfif:source_date>1999-02-03T04:05:06Z</pfif:source_date>
    <pfif:entry_date>1999-02-03T04:05:06Z</pfif:entry_date>
    <pfif:other>data still here</pfif:other>
  </pfif:person>
</pfif:pfif>"""

XML_EXPIRE_99_NO_DATA_NONSYNCED_DATES = """<?xml version="1.0"
  encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/id1</pfif:person_record_id>
    <pfif:expiry_date>1999-02-03T04:05:06Z</pfif:expiry_date>
    <pfif:source_date>1998-02-03T04:05:06Z</pfif:source_date>
    <pfif:entry_date>1999-02-03T04:05:06Z</pfif:entry_date>
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id>example.org/id2</pfif:person_record_id>
    <pfif:expiry_date>1999-02-03T04:05:06Z</pfif:expiry_date>
    <pfif:source_date>1999-04-03T04:05:06Z</pfif:source_date>
    <pfif:entry_date>1999-04-03T04:05:06Z</pfif:entry_date>
  </pfif:person>
</pfif:pfif>"""

XML_EXPIRE_99_12 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id>example.org/id1</pfif:person_record_id>
    <pfif:expiry_date>1999-02-03T04:05:06Z</pfif:expiry_date>
    <pfif:source_date>1999-02-03T04:05:06Z</pfif:source_date>
    <pfif:entry_date>1999-02-03T04:05:06Z</pfif:entry_date>
    <pfif:other>data still here</pfif:other>
  </pfif:person>
</pfif:pfif>"""

XML_EXPIRE_99_HAS_NOTE_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/id</pfif:person_record_id>
    <pfif:expiry_date>1999-02-03T04:05:06Z</pfif:expiry_date>
    <pfif:source_date>1999-02-03T04:05:06Z</pfif:source_date>
    <pfif:entry_date>1999-02-03T04:05:06Z</pfif:entry_date>
  </pfif:person>
  <pfif:note>
    <pfif:person_record_id>example.org/id</pfif:person_record_id>
    <pfif:note_record_id>example.org/note/not/deleted</pfif:note_record_id>
  </pfif:note>
</pfif:pfif>"""

XML_NO_EXPIRY_DATE = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/id1</pfif:person_record_id>
    <pfif:source_date>1999-02-03T04:05:06Z</pfif:source_date>
    <pfif:entry_date>1999-02-03T04:05:06Z</pfif:entry_date>
    <pfif:other>data still here</pfif:other>
  </pfif:person>
</pfif:pfif>"""

XML_EMPTY_EXPIRY_DATE = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/id1</pfif:person_record_id>
    <pfif:expiry_date></pfif:expiry_date>
    <pfif:source_date>1999-02-03T04:05:06Z</pfif:source_date>
    <pfif:entry_date>1999-02-03T04:05:06Z</pfif:entry_date>
    <pfif:other>data still here</pfif:other>
  </pfif:person>
</pfif:pfif>"""

XML_UNLINKED_RECORDS = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/p1</pfif:person_record_id>
    <pfif:note>
      <pfif:note_record_id>example.com/n1</pfif:note_record_id>
    </pfif:note>
  </pfif:person>
</pfif:pfif>"""

XML_CORRECTLY_LINKED_RECORDS = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/p1</pfif:person_record_id>
    <pfif:note>
      <pfif:note_record_id>example.com/n1</pfif:note_record_id>
      <pfif:linked_person_record_id>example.org/p2</pfif:linked_person_record_id>
    </pfif:note>
  </pfif:person>
  <pfif:note>
    <pfif:note_record_id>example.com/n2</pfif:note_record_id>
    <pfif:person_record_id>example.org/p2</pfif:person_record_id>
    <pfif:linked_person_record_id>example.org/p1</pfif:linked_person_record_id>
  </pfif:note>
</pfif:pfif>"""

XML_ASYMMETRICALLY_LINKED_RECORDS = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:note>
    <pfif:note_record_id>example.com/n2</pfif:note_record_id>
    <pfif:person_record_id>example.org/p2</pfif:person_record_id>
    <pfif:linked_person_record_id>example.org/p1</pfif:linked_person_record_id>
  </pfif:note>
</pfif:pfif>"""

XML_GIBBERISH_FIELDS = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id>example.org/id1</pfif:person_record_id>
    <pfif:expiry_date />
    <pfif:field />
    <pfif:foo />
    <pfif:note>
      <pfif:bar />
    </pfif:note>
  </pfif:person>
  <pfif:note>
    <pfif:bar />
  </pfif:note>
</pfif:pfif>"""

XML_DUPLICATE_FIELDS = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/id1</pfif:person_record_id>
    <pfif:expiry_date />
    <pfif:expiry_date />
    <pfif:expiry_date />
    <pfif:note>
      <pfif:note_record_id />
      <pfif:note_record_id />
      <pfif:person_record_id />
    </pfif:note>
    <pfif:note>
      <pfif:note_record_id />
    </pfif:note>
  </pfif:person>
  <pfif:note>
    <pfif:note_record_id />
  </pfif:note>
</pfif:pfif>"""

XML_TOP_LEVEL_NOTE_PERSON_11 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:note />
  <pfif:person>
    <pfif:person_record_id>example.org/id1</pfif:person_record_id>
    <pfif:note>
      <pfif:note_record_id />
    </pfif:note>
  </pfif:person>
  <pfif:note>
    <pfif:note_record_id />
  </pfif:note>
</pfif:pfif>"""

XML_TWO_DUPLICATE_NO_CHILD = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.1">
  <pfif:foo />
  <pfif:foo />
</pfif:pfif>"""

XML_UNICODE_12 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.2">
  <pfif:person>
    <pfif:person_record_id>not.unicode/person-id</pfif:person_record_id>
    <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
    <pfif:author_name>ユニコード名</pfif:author_name>
    <pfif:first_name>اسم يونيكود</pfif:first_name>
    <pfif:last_name>Unicode名称</pfif:last_name>
    <pfif:home_street>Юнікодам вуліцы</pfif:home_street>
    <pfif:home_city>ইউনিকোড শহর</pfif:home_city>
    <pfif:home_neighborhood>Unicode השכונה</pfif:home_neighborhood>
    <pfif:other>ಯುನಿಕೋಡಿನ ಇತರ</pfif:other>
    <pfif:note>
      <pfif:note_record_id>not.unicode/note-id</pfif:note_record_id>
      <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
      <pfif:author_name>유니 코드 이름</pfif:author_name>
      <pfif:last_known_location>محل یونیکد</pfif:last_known_location>
      <pfif:text>Unicode текст</pfif:text>
    </pfif:note>
  </pfif:person>
  <pfif:note>
    <pfif:note_record_id>not.unicode/note-id-2</pfif:note_record_id>
    <pfif:person_record_id>note.unicode/person-id</pfif:person_record_id>
    <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
    <pfif:author_name>Уницоде имена</pfif:author_name>
    <pfif:last_known_location>யுனிகோட் இடம்</pfif:last_known_location>
    <pfif:text>యూనికోడ్ టెక్స్ట్</pfif:text>
  </pfif:note>
</pfif:pfif>"""

XML_MANDATORY_13 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/person</pfif:person_record_id>
    <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
    <pfif:full_name>Full Name</pfif:full_name>
    <pfif:note>
      <pfif:person_record_id>example.org/person</pfif:person_record_id>
      <pfif:note_record_id>example.org/sub-note</pfif:note_record_id>
      <pfif:author_name>Author Name</pfif:author_name>
      <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
      <pfif:text>Lots of Text</pfif:text>
    </pfif:note>
  </pfif:person>
  <pfif:note>
    <pfif:note_record_id>example.org/non-sub-note</pfif:note_record_id>
    <pfif:person_record_id>example.org/person2</pfif:person_record_id>
    <pfif:author_name>Author Name</pfif:author_name>
    <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
    <pfif:text>Lots of Text</pfif:text>
  </pfif:note>
</pfif:pfif>"""

XML_MANDATORY_13_SUBNOTE = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/person</pfif:person_record_id>
    <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
    <pfif:full_name>Full Name</pfif:full_name>
    <pfif:note>
      <pfif:note_record_id>example.org/note</pfif:note_record_id>
      <pfif:author_name>Author Name</pfif:author_name>
      <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
      <pfif:text>Lots of Text</pfif:text>
    </pfif:note>
  </pfif:person>
</pfif:pfif>"""

XML_MANDATORY_13_NONSUB = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/person</pfif:person_record_id>
    <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
    <pfif:full_name>Full Name</pfif:full_name>
  </pfif:person>
  <pfif:note>
    <pfif:person_record_id>example.org/person</pfif:person_record_id>
    <pfif:note_record_id>example.org/note</pfif:note_record_id>
    <pfif:author_name>Author Name</pfif:author_name>
    <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
    <pfif:text>Lots of Text</pfif:text>
  </pfif:note>
</pfif:pfif>"""

XML_MANDATORY_13_MAP = {
    'example.org/person' : {'person_record_id' : 'example.org/person',
                            'source_date' : '1234-56-78T90:12:34Z',
                            'full_name' : 'Full Name'},
    'example.org/sub-note' : {'person_record_id' : 'example.org/person',
                              'note_record_id' : 'example.org/sub-note',
                              'source_date' : '1234-56-78T90:12:34Z',
                              'author_name' : 'Author Name',
                              'text' : 'Lots of Text'},
    'example.org/non-sub-note' : {'person_record_id' : 'example.org/person2',
                                  'note_record_id' : 'example.org/non-sub-note',
                                  'source_date' : '1234-56-78T90:12:34Z',
                                  'author_name' : 'Author Name',
                                  'text' : 'Lots of Text'}}

# full_name and author_name are ignored
XML_MANDATORY_13_IGNORE_NAMES_MAP = {
    'example.org/person' : {'person_record_id' : 'example.org/person',
                            'source_date' : '1234-56-78T90:12:34Z'},
    'example.org/sub-note' : {'person_record_id' : 'example.org/person',
                              'note_record_id' : 'example.org/sub-note',
                              'source_date' : '1234-56-78T90:12:34Z',
                              'text' : 'Lots of Text'},
    'example.org/non-sub-note' : {'person_record_id' : 'example.org/person2',
                                  'note_record_id' : 'example.org/non-sub-note',
                                  'source_date' : '1234-56-78T90:12:34Z',
                                  'text' : 'Lots of Text'}}

XML_BLANK_FIELDS = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/person</pfif:person_record_id>
    <pfif:source_date></pfif:source_date>
  </pfif:person>
</pfif:pfif>"""

XML_BLANK_FIELDS_MAP =  {
    'example.org/person' : {'person_record_id' : 'example.org/person',
                            'source_date' : ''}}

XML_ONLY_RECORD_MAP =  {
    'example.org/person' : {'person_record_id' : 'example.org/person'}}

XML_ONE_BLANK_RECORD_ID = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/person</pfif:person_record_id>
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id></pfif:person_record_id>
  </pfif:person>
</pfif:pfif>"""

XML_ONE_PERSON_ONE_FIELD = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/person</pfif:person_record_id>
  </pfif:person>
</pfif:pfif>"""

XML_TWO_PERSONS_ONE_FIELD = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/person</pfif:person_record_id>
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id>example.org/person2</pfif:person_record_id>
  </pfif:person>
</pfif:pfif>"""

XML_ONE_PERSON_TWO_FIELDS = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/person</pfif:person_record_id>
    <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
  </pfif:person>
</pfif:pfif>"""

XML_ONE_PERSON_TWO_FIELDS_NEW_VALUE = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/person</pfif:person_record_id>
    <pfif:source_date>abcd1234-56-78T90:12:34Z</pfif:source_date>
  </pfif:person>
</pfif:pfif>"""

XML_ADDED_DELETED_CHANGED_1 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/person1</pfif:person_record_id>
    <pfif:source_date>1234-56-78T90:12:34Z</pfif:source_date>
    <pfif:foo />
  </pfif:person>
  <pfif:person>
    <pfif:person_record_id>example.org/person2</pfif:person_record_id>
  </pfif:person>
</pfif:pfif>"""

XML_ADDED_DELETED_CHANGED_2 = """<?xml version="1.0" encoding="UTF-8"?>
<pfif:pfif xmlns:pfif="http://zesty.ca/pfif/1.3">
  <pfif:person>
    <pfif:person_record_id>example.org/person1</pfif:person_record_id>
    <pfif:source_date>1234-56-78t90:12:34z</pfif:source_date>
    <pfif:bar />
  </pfif:person>
  <pfif:note>
    <pfif:note_record_id>example.org/person2</pfif:note_record_id>
  </pfif:note>
</pfif:pfif>"""
