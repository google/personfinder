#!/usr/bin/python2.5
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
from model import db

from django.utils.translation import ugettext as _

class ConfirmEnableCommentsError(Exception):
    """Container for user-facing error messages when confirming to disable 
    future comments to a record."""
    pass

class ConfirmEnableComments(utils.Handler):
    """This handler lets the author confirm to disable future comments 
    to a person record."""

    def get(self):
        try:
            person, token = self.get_person_and_verify_params()
        except ConfirmEnableCommentsError, e:
            return self.error(400, unicode(e))

        # Log the user action.
        model.UserActionLog.put_new('enable_comments', person)

        self.update_person_record(person)

        record_url = self.get_url(
            '/view', id=person.record_id, subdomain=person.subdomain)

        # Send subscribers a notice email.
        subject = _(
            '[Person Finder] Enabling comments notice for '
            '"%(first_name)s %(last_name)s"'
        ) % {
            'first_name': person.first_name,
            'last_name': person.last_name
        }
        email_addresses = person.get_associated_emails()
        for address in email_addresses:
            self.send_mail(
                subject=subject,
                to=address,
                body=self.render_to_string(
                    'enable_comments_notice_email.txt',
                    first_name=person.first_name,
                    last_name=person.last_name,
                    record_url=record_url
                )
            )

        self.redirect(record_url)
 

    def post(self):
        try:
            person, token = self.get_person_and_verify_params()
        except ConfirmEnableCommentsError, e:
            return self.error(400, unicode(e))

        # Log the user action.
        model.UserActionLog.put_new('enable_comments', person)

        self.update_person_record(person)

        record_url = self.get_url(
            '/view', id=person.record_id, subdomain=person.subdomain)

        # Send subscribers a notice email.
        subject = _(
            '[Person Finder] Enabling comments notice for '
            '"%(first_name)s %(last_name)s"'
        ) % {
            'first_name': person.first_name,
            'last_name': person.last_name
        }
        email_addresses = person.get_associated_emails()
        for address in email_addresses:
            self.send_mail(
                subject=subject,
                to=address,
                body=self.render_to_string(
                    'enable_comments_notice_email.txt',
                    first_name=person.first_name,
                    last_name=person.last_name,
                    record_url=record_url
                )
            )

        self.redirect(record_url)

    def update_person_record(self, person):
        """Update the comments_disabled flag in person record."""
        person.comments_disabled = False
        db.put([person])
        return

    def get_person_and_verify_params(self):
        """Check the request for a valid person id and valid crypto token.

        Returns a tuple containing: (person, token)

        If there is an error we raise a ConfirmDisableCommentsError. """
        person = model.Person.get_by_key_name(self.params.id)
        if not person:
            raise ConfirmEnableCommentsError(
                'No person with ID: %r' % self.params.id)

        token = self.request.get('token')
        data = 'enable_comments:%s' % self.params.id
        if not reveal.verify(data, token):
            raise ConfirmEnableCommentsError('The token was invalid')

        return (person, token)

if __name__ == '__main__':
    utils.run(('/confirm_enable_comments', ConfirmEnableComments))
