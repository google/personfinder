#!/usr/bin/python2.7
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

import const
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


class Handler(utils.BaseHandler):
    admin_required = True
    def get(self):
        if not self.is_current_user_authorized():
            return self.redirect(users.create_login_url('/admin/review'))

        # Make the navigation links.
        status = self.request.get('status') or 'all'
        source = self.request.get('source') or 'all'

        status_nav_html = ''
        for option in [
            'all', 'unspecified', 'information_sought', 'is_note_author',
            'believed_alive', 'believed_missing', 'believed_dead']:
            if option == status:
                status_nav_html += '<b>%s</b>&nbsp; ' % option
            else:
                status_nav_html += '<a href="%s">%s</a>&nbsp; ' % (
                    self.get_url('/admin/review', status=option, source=source),
                    option)

        source_nav_html = ''
        source_options = ['all', '%s.%s' % (self.repo, const.HOME_DOMAIN)]
        for auth_key in model.Authorization.all().filter('repo =', self.repo):
            if auth_key.domain_write_permission:
                source_options.append(auth_key.domain_write_permission)
        for option in source_options:
            if option == source:
                source_nav_html += '<b>%s</b>&nbsp; ' % option
            else:
                source_nav_html += '<a href="%s">%s</a>&nbsp; ' % (
                    self.get_url('/admin/review', status=status, source=option),
                    option)

        #
        # Construct the query for notes.
        query = model.Note.all_in_repo(self.repo
                         ).filter('reviewed =', False
                         ).filter('hidden =', False)
        if status == 'unspecified':
            query.filter('status =', '')
        elif status != 'all':
            query.filter('status =', status)
        if source != 'all':
            query.filter('person_record_id >=', '%s/' % source)
            query.filter('person_record_id <', '%s0' % source)
            # TODO(ryok): we really want to order by entry_date, but GAE
            # restriction applies here, and we can not use two different
            # properties for comparison and ordering. The proper solution seems
            # to add a property source_domain to Note.
            query.order('-person_record_id')
        else:
            query.order('-entry_date')

        skip = self.params.skip or 0
        notes = query.fetch(NOTES_PER_PAGE + 1, skip)
        for note in notes[:NOTES_PER_PAGE]:
            person = model.Person.get(self.repo, note.person_record_id)
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
                note.source_date_string = self.format_datetime_localized(
                    note.source_date);
                note.entry_date_string = self.format_datetime_localized(
                    note.entry_date);

        if len(notes) > NOTES_PER_PAGE:
            notes = notes[:NOTES_PER_PAGE]
            next_skip = skip + NOTES_PER_PAGE
            next_url = self.get_url(
                '/admin/review', skip=str(next_skip),
                status=status, source=source)
        else:
            next_url = None

        user = users.get_current_user()
        xsrf_tool = utils.XsrfTool()
        return self.render(
            'admin_review.html',
            notes=notes,
            status_nav_html=status_nav_html,
            source_nav_html=source_nav_html,
            next_url=next_url,
            first=skip + 1,
            last=skip + len(notes[:NOTES_PER_PAGE]),
            xsrf_token=xsrf_tool.generate_token(
                user.user_id(), 'admin_review'))

    def post(self):
        user = users.get_current_user()
        xsrf_tool = utils.XsrfTool()
        if not (self.params.xsrf_token and xsrf_tool.verify_token(
                    self.params.xsrf_token, user.user_id(), 'admin_review')):
            self.error(403)
            return False
        if not self.is_current_user_authorized():
            return self.redirect(users.create_login_url('/admin/review'))

        notes = []
        for name, value in self.request.params.items():
            if name.startswith('note.'):
                note = model.Note.get(self.repo, name[5:])
                if note:
                    if value in ['accept', 'flag']:
                        note.reviewed = True
                    if value == 'flag':
                        note.hidden = True
                    notes.append(note)
        db.put(notes)
        self.redirect('/admin/review',
                      status=self.params.status,
                      source=self.params.source,
                      skip=str(self.params.skip))

    def is_current_user_authorized(self):
        if users.is_current_user_admin():  # admins can always review
            return True
        domain = self.config.authorized_reviewer_domain
        if domain:  # also allow any user from the configured domain
            user = users.get_current_user()
            return user and user.email().endswith('@' + domain)
