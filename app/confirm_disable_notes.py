#!/usr/bin/python2.7
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import reveal

import model
import utils
from google.appengine.ext import db

from django.utils.translation import ugettext as _

class DisableAndEnableNotesError(Exception):
    """Container for user-facing error messages when confirming to disable
    or enable future nots to a record."""
    pass

class Handler(utils.BaseHandler):
    """This handler lets the author confirm to disable future notes 
    to a person record."""

    def get(self):
        try:
            person, token = self.get_person_and_verify_params()
        except DisableAndEnableNotesError, e:
            return self.error(400, unicode(e))

        self.render('confirm_disable_notes.html',
                    person=person,
                    id=self.params.id,
                    token=token)

    def post(self):
        try:
            person, token = self.get_person_and_verify_params()
        except DisableAndEnableNotesError, e:
            return self.error(400, unicode(e))

        # Log the user action.
        model.UserActionLog.put_new(
            'disable_notes',
            person,
            self.request.get('reason_for_disabling_notes'))

        # Update the notes_disabled flag in person record.
        person.notes_disabled = True
        person.put()

        record_url = self.get_url(
            '/view', id=person.record_id, repo=person.repo)

        # Send subscribers a notice email.
        subject = _('[Person Finder] Notes are now disabled for "%(full_name)s"'
                ) % {'full_name': person.primary_full_name}
        email_addresses = person.get_associated_emails()
        for address in email_addresses:
            self.send_mail(
                subject=subject,
                to=address,
                body=self.render_to_string(
                    'disable_notes_notice_email.txt',
                    full_name=person.primary_full_name,
                    record_url=record_url
                )
            )

        self.redirect(record_url)

    def get_person_and_verify_params(self):
        """Check the request for a valid person id and valid crypto token.
        Returns a tuple containing: (person, token)
        If there is an error we raise a DisableAndEnableNotesError. """
        person = model.Person.get_by_key_name(self.params.id)
        if not person:
            # Place holder name here is id_str, not id, because
            # the translation system doesn't allow the same string in both
            # a place holder name and a normal uppercase word in one message.
            raise DisableAndEnableNotesError(
                _('No person with ID: %(id_str)s.')
                % {'id_str': self.params.id})

        token = self.request.get('token')
        data = 'disable_notes:%s' % self.params.id
        if not reveal.verify(data, token):
            raise DisableAndEnableNotesError(
                _("The token %(token)s was invalid.") % {'token': token})

        return (person, token)
