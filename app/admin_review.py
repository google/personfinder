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

import logging

from google.appengine.ext import db
from google.appengine.api import users

import model
import utils

NOTES_PER_PAGE = 50
STATUS_CODES = {
  None: 'u',
  '': 'u',
  'information_sought': 's',
  'believed_alive': 'a',
  'believed_missing': 'm',
  'believed_dead': 'd',
  'is_note_author': 'i',
}


class Review(utils.Handler):
    def get(self):
        if not self.is_current_user_authorized():
            return self.redirect(users.create_login_url('/admin/review'))

        # Make the navigation links.
        status = self.request.get('status') or 'all'
        nav_html = ''
        for option in [
            'all', 'unspecified', 'information_sought', 'is_note_author',
            'believed_alive', 'believed_missing', 'believed_dead']:
            if option == status:
                nav_html += '<b>%s</b>&nbsp; ' % option
            else:
                nav_html += '<a href="%s">%s</a>&nbsp; ' % (
                    self.get_url('/admin/review', status=option), option)

        # Construct the query for notes.
        query = model.Note.all_in_subdomain(self.subdomain
                         ).filter('reviewed =', False
                         ).filter('hidden =', False
                         ).order('-entry_date')
        if status == 'unspecified':
            query.filter('status =', '')
        elif status != 'all':
            query.filter('status =', status)

        skip = self.params.skip or 0
        notes = query.fetch(NOTES_PER_PAGE + 1, skip)
        for note in notes[:NOTES_PER_PAGE]:
            person = model.Person.get(self.subdomain, note.person_record_id)
            if person:
                # Copy in the fields of the associated Person.
                for name in person.properties():
                    setattr(note, 'person_' + name, getattr(person, name))

                # Get the statuses of the other notes on this Person.
                status_codes = ''
                for other_note in person.get_notes():
                    code = STATUS_CODES[other_note.status]
                    if other_note.note_record_id == note.note_record_id:
                        code = code.upper()
                    status_codes += code
                note.person_status_codes = status_codes

        if len(notes) > NOTES_PER_PAGE:
            notes = notes[:NOTES_PER_PAGE]
            next_skip = skip + NOTES_PER_PAGE
            next_url = self.get_url(
                '/admin/review', skip=str(next_skip), status=status)
        else:
            next_url = None

        return self.render(
            'templates/admin_review.html',
            notes=notes, nav_html=nav_html, next_url=next_url,
            first=skip + 1, last=skip + len(notes[:NOTES_PER_PAGE]))

    def post(self):
        if not self.is_current_user_authorized():
            return self.redirect(users.create_login_url('/admin/review'))

        notes = []
        for name, value in self.request.params.items():
            if name.startswith('note.'):
                note = model.Note.get(self.subdomain, name[5:])
                if note:
                    if value in ['accept', 'flag']:
                        note.reviewed = True
                    if value == 'flag':
                        note.hidden = True
                    notes.append(note)
        db.put(notes)
        self.redirect('/admin/review', status=self.params.status)

    def is_current_user_authorized(self):
        if users.is_current_user_admin():  # admins can always review
            return True
        domain = self.config.authorized_reviewer_domain
        if domain:  # also allow any user from the configured domain
            user = users.get_current_user()
            return user and user.email().endswith('@' + domain)


if __name__ == '__main__':
    utils.run(('/admin/review', Review))
