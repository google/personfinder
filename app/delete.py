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

# The length of time an expired record exists before our
# cron job will remove it from the database. Deletion reversals can only
# happen while a expired person record still exists.
EXPIRED_TTL_DAYS = 3 # days

class Delete(utils.Handler):
    """Delete a person and dependent entities."""

    def get(self):
        """Prompt the user with a captcha to carry out the deletion."""
        person = model.Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        self.render('templates/delete.html',
                    person=person,
                    view_url=self.get_url('/view', id=self.params.id),
                    captcha_html=self.get_captcha_html())

    def post(self):
        """If the captcha is valid, set expirey_date for a delayed deletion

        Otherwise, prompt the user with a new captcha.

        The record becomes inaccessible immediately, but doesn't get deleted
        until the EXPIRED_TTL_DAYS has passed.  
        """        
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
            # set the expired flag.
            person.expiry_date = utils.get_utcnow()
            # mark the deletion.
            reason_for_deletion = self.request.get('reason_for_deletion')
            person.mark_for_delete()
            # add the PersonAction for future ref.
            model.PersonAction(person_record_id=person.record_id, 
                       subdomain=person.subdomain, time=utils.get_utcnow(),
                       reason_for_report=reason_for_deletion,
                       is_delete=True).put()        
            # an unfortunate name for this method - 200 is http OK.
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
