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

from model import *
from utils import *
import prefix
import pfif
import reveal
import sys

# Fields to show for side-by-side comparison.
COMPARE_FIELDS = pfif.PFIF_1_2.fields['person']


class MultiView(Handler):
    def get(self):
        # To handle multiple persons, we create a single object where
        # each property is a list of values, one for each person.
        # This makes page rendering easier.
        person = dict([(prop, []) for prop in COMPARE_FIELDS])
        any = dict([(prop, None) for prop in COMPARE_FIELDS])

        # Get all persons from db.
        # TODO: Can later optimize to use fewer DB calls.
        for i in [1, 2, 3]:
            id = self.request.get('id%d' % i)
            if not id:
                break
            p = Person.get(self.subdomain, id)

            for prop in COMPARE_FIELDS:
                val = getattr(p, prop)
                if prop == 'sex':  # convert enum value to localized text
                    val = get_person_sex_text(p)
                person[prop].append(val)
                any[prop] = any[prop] or val

        # Check if private info should be revealed.
        content_id = 'multiview:' + ','.join(person['person_record_id'])
        reveal_url = reveal.make_reveal_url(self, content_id)
        show_private_info = reveal.verify(content_id, self.params.signature)

        # TODO: Handle no persons found.

        # Add a calculated full name property - used in the title.
        person['full_name'] = [
            fname + ' ' + lname
            for fname, lname in zip(person['first_name'], person['last_name'])]
        standalone = self.request.get('standalone')

        # Note: we're not showing notes and linked persons information
        # here at the moment.
        self.render('templates/multiview.html',
                    person=person, any=any, standalone=standalone,
                    cols=len(person['first_name']) + 1,
                    onload_function='view_page_loaded()', markdup=True,
                    show_private_info=show_private_info, reveal_url=reveal_url)

    def post(self):
        if not self.params.text:
            return self.error(
                200, _('Message is required. Please go back and try again.'))

        if not self.params.author_name:
            return self.error(
                200, _('Your name is required in the "About you" section.  Please go back and try again.'))

        # TODO: To reduce possible abuse, we currently limit to 3 person
        # match. We could guard using e.g. an XSRF token, which I don't know how
        # to build in GAE.

        ids = set()
        for i in [1, 2, 3]:
            id = getattr(self.params, 'id%d' % i)
            if not id:
                break
            ids.add(id)

        if len(ids) > 1:
            notes = []
            for person_id in ids:
                for other_id in ids - set([person_id]):
                    note = Note.create_original(
                        self.subdomain,
                        person_record_id=person_id,
                        linked_person_record_id=other_id,
                        text=self.params.text,
                        author_name=self.params.author_name,
                        author_phone=self.params.author_phone,
                        author_email=self.params.author_email,
                        source_date=get_utcnow())
                    notes.append(note)
            db.put(notes)
        self.redirect('/view', id=self.params.id1)

if __name__ == '__main__':
    run(('/multiview', MultiView))
