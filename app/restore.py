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

from google.appengine.api import mail
from recaptcha.client import captcha

from model import db
import model
import reveal
import utils

from django.utils.translation import ugettext as _

class RestoreError(Exception): 
    """Error for missing expired record."""
    pass

class Restore(utils.Handler):
    """Used to restore a record from deleted/expired status. It will "undelete"
    a previously deleted record, as long as the person has not already
    been removed from the system."""

    def get(self):
        """Prompts a user with a CAPTCHA to re-instate the supplied record.
        There must be a valid token supplied as post param "token"."""
        try:
            person, token = self.get_person_and_verify_params()
        except RestoreError, err:
            return self.error(400, unicode(err))

        self.render('templates/restore.html',
                    captcha_html=self.get_captcha_html(),
                    token=token, id=self.params.id)

    def post(self):
        """If the submitted CAPTCHA is valid, re-instates the record and
        removes the person. Otherwise, display another CAPTCHA to the
        user for authentication."""

        captcha_response = self.get_captcha_response()
        try: 
            person, token = self.get_person_and_verify_params()
        except RestoreError, err:
            return self.error(400, unicode(err))

        if not captcha_response.is_valid and not self.is_test_mode():
            captcha_html = self.get_captcha_html(captcha_response.error_code)
            self.render('templates/restore.html',
                        captcha_html=captcha_html, token=token,
                        id=self.params.id)
            return

        person.mark_for_delete(delete=False)

        model.PersonFlag(person_record_id=person.record_id,
                         subdomain=person.subdomain, time=utils.get_utcnow(),
                         is_delete=False).put()

        record_url = self.get_url(
            '/view', id=person.record_id, subdomain=person.subdomain)
        subject = _(
            '[Person Finder] Record restoration notice for '
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
                    'restoration_email.txt',
                    first_name=person.first_name,
                    last_name=person.last_name,
                    record_url=record_url
                )
            )

        self.redirect(record_url)
        
    def get_person_and_verify_params(self):
        """Checks the request for a valid person id and valid crypto token.

        Returns a tuple containing: (person, token)
            
        If there is an error we raise an error, instead of pretending we're
        using C."""
        person = model.Person.get_by_key_name(self.params.id)
        if not person:
            raise RestoreError(
                'The record with the following ID no longer exists: %s' %
                self.params.id.split(':', 1)[1])
        token = self.request.get('token')
        data = 'restore:%s' % self.params.id
        if not reveal.verify(data, token):
            raise RestoreError('invalid token')
        return (person, token)


if __name__ == '__main__':
    utils.run(('/restore', Restore))
