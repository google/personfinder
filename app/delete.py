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

# The number of days an expired record lingers before the DeleteExpired task
# wipes it from the database.  When a user deletes a record through the UI,
# we carry that out by setting the expiry to the current time, so this is also
# the number of days after deletion during which the record can be restored.
EXPIRED_TTL_DAYS = 3

class Delete(utils.Handler):
    """Handles a user request to delete a person record."""

    def get(self):
        """Prompts the user with a Turing test before carrying out deletion."""
        person = model.Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        self.render('templates/delete.html',
                    person=person,
                    view_url=self.get_url('/view', id=self.params.id),
                    captcha_html=self.get_captcha_html())

    def post(self):
        """If the user answered the Turing test correctly, "delete" the record
        by setting the expiry_date to the current time.  The record becomes
        inaccessible immediately, but its contents are not actually deleted
        EXPIRED_TTL_DAYS days have passed."""        
        person = model.Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        captcha_response = self.get_captcha_response()
        if self.is_test_mode() or captcha_response.is_valid:

            email_addresses = person.get_associated_emails()

            # i18n: Subject line of an e-mail message notifying a user
            # i18n: that a person record has been deleted
            subject = _(
                '[Person Finder] Deletion notice for '
                '"%(first_name)s %(last_name)s"'
            ) % {'first_name': person.first_name, 'last_name': person.last_name}

            # Send e-mail to all the addresses notifying them of the deletion.
            for email in email_addresses:
                if email == person.author_email:
                    template_name = 'deletion_email_for_person_author.txt'
                else:
                    template_name = 'deletion_email_for_note_author.txt'
                self.send_mail(
                    subject=subject,
                    to=email,
                    body=self.render_to_string(
                        template_name,
                        first_name=person.first_name,
                        last_name=person.last_name,
                        site_url=self.get_url('/'),
                        days_until_deletion=EXPIRED_TTL_DAYS,
                        restore_url=self.get_restore_url(person)
                    )
                )

            # Log the user action.
            model.UserActionLog.put_new(
                'delete', person, self.request.get('reason_for_deletion'))

            # TODO(kpy): For a clone record, just delete the record instead
            # of changing the expiry_date and leaving a placeholder.

            # Set the expiry_date to now, and set is_expired flags to match.
            person.expiry_date = utils.get_utcnow()
            person.put_expiry_flags()
            return self.info(200, _('The record has been deleted.'))
        else:
            captcha_html = self.get_captcha_html(captcha_response.error_code)
            self.render('templates/delete.html', person=person,
                        view_url=self.get_url('/view', id=self.params.id),
                        captcha_html=captcha_html)

    def get_restore_url(self, person, ttl=3*24*3600):
        """Returns a URL to be used for restoring a deleted person record.
        The default TTL for a restoration URL is 3 days."""
        key_name = person.key().name()
        data = 'restore:%s' % key_name 
        token = reveal.sign(data, ttl)
        return self.get_url('/restore', token=token, id=key_name)


if __name__ == '__main__':
    utils.run(('/delete', Delete))
