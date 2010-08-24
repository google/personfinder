#!/usr/bin/python2.5
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

"""Handler for Atom PFIF 1.2 person and note feeds."""

__author__ = 'kpy@google.com (Ka-Ping Yee)'

import atom
import datetime
import model
import pfif
import utils

HARD_MAX_RESULTS = 200  # Clients can ask for more, but won't get more.
MAX_SKIP = 800  # App Engine imposes a limit of 1000 on max_results + skip.


def get_latest_entry_date(entities):
    if entities:
        return max(entity.entry_date for entity in entities)
    else:
        return datetime.datetime.now()

class Person(utils.Handler):
    def get(self):
        max_results = min(self.params.max_results or 10, HARD_MAX_RESULTS)
        skip = min(self.params.skip or 0, MAX_SKIP)
        if self.params.omit_notes:  # Return only the person records.
            get_notes_for_person = lambda person: []
        else:
            def get_notes_for_person(person):
                notes = model.Note.get_by_person_record_id(
                    person['person_record_id'])
                records = map(pfif.PFIF_1_2.note_to_dict, notes)
                utils.filter_sensitive_fields(records, self.request)
                return records

        if self.params.min_entry_date:  # Scan forward.
            query = model.Person.all().order('entry_date').filter(
                'entry_date >=', self.params.min_entry_date)
        else:  # Show recent entries, scanning backward.
            query = model.Person.all().order('-entry_date')

        persons = query.fetch(max_results, skip)
        updated = get_latest_entry_date(persons)

        self.response.headers['Content-Type'] = 'application/xml'
        records = map(pfif.PFIF_1_2.person_to_dict, persons)
        utils.filter_sensitive_fields(records, self.request)
        atom.ATOM_PFIF_1_2.write_person_feed(
            self.response.out, records, get_notes_for_person,
            self.request.url, self.env.netloc, '', updated)


class Note(utils.Handler):
    def get(self):
        max_results = min(self.params.max_results or 10, HARD_MAX_RESULTS)
        skip = min(self.params.skip or 0, MAX_SKIP)

        if self.params.min_entry_date:  # Scan forward.
            query = model.Note.all().order('entry_date').filter(
                'entry_date >=', self.params.min_entry_date)
        else:  # Show recent entries, scanning backward.
            query = model.Note.all().order('-entry_date')

        if self.params.person_record_id:  # Show notes for a specific person.
            query = query.filter(
                'person_record_id = ', self.params.person_record_id)

        notes = query.fetch(max_results, skip)
        updated = get_latest_entry_date(notes)

        self.response.headers['Content-Type'] = 'application/xml'
        records = map(pfif.PFIF_1_2.note_to_dict, notes)
        utils.filter_sensitive_fields(records, self.request)
        atom.ATOM_PFIF_1_2.write_note_feed(
            self.response.out, records, self.request.url,
            self.env.netloc, '', updated)

if __name__ == '__main__':
    utils.run(('/feeds/person', Person), ('/feeds/note', Note))
