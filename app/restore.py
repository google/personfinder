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

class Restore(utils.Handler):
    """Used to restore a record from tombstone status. It will "undelete"
    a previously deleted record, as long as the tombstone has not already
    been removed from the system."""

    def get(self):
        """Prompts a user with a CAPTCHA to re-instate the supplied record.
        There must be a valid token supplied as post param "token"."""
        tombstone, token, error = self.get_tombstone_and_verify_params()
        if error:
            return self.error(400, error)

        self.render('templates/restore.html',
                    captcha_html=self.get_captcha_html(),
                    token=token, id=self.params.id)

    def post(self):
        """If the submitted CAPTCHA is valid, re-instates the record and
        removes the tombstone. Otherwise, display another CAPTCHA to the
        user for authentication."""
        tombstone, token, error = self.get_tombstone_and_verify_params()
        if error:
            return self.error(400, error)

        captcha_response = self.get_captcha_response()
        if not captcha_response.is_valid and not self.is_test_mode():
            captcha_html = self.get_captcha_html(captcha_response.error_code)
            self.render('templates/restore.html',
                        captcha_html=captcha_html, token=token,
                        id=self.params.id)
            return

        person_props = model.get_properties_as_dict(tombstone)
        person_props.update(entry_date=utils.get_utcnow())
        new_person = model.Person.create_original(
            **model.get_properties_as_dict(tombstone))
        # Necessary to stop the record from displaying 'None' as the last name
        # if one is not present in the original record
        if not getattr(new_person, 'last_name'):
            new_person.last_name = ''

        note_tombstones = model.NoteTombstone.get_by_tombstone_record_id(
            tombstone.subdomain, tombstone.record_id)
        def process(note):
            """Helper function: processes note tombstones into new notes."""
            new_note = model.Note.create_original(
                **model.get_properties_as_dict(note))
            new_note.person_record_id = new_person.record_id
            return new_note
        new_notes = [process(n) for n in note_tombstones]

        db.put(new_notes + [new_person])
        db.delete(note_tombstones + [tombstone])
        model.PersonFlag(subdomain=tombstone.subdomain, time=utils.get_utcnow(),
                         person_record_id=tombstone.record_id,
                         new_person_record_id=new_person.record_id,
                         is_delete=False).put()

        record_url = self.get_url(
            '/view', id=new_person.record_id, subdomain=new_person.subdomain)
        subject = _(
            '[Person Finder] Record restoration notice for '
            '"%(first_name)s %(last_name)s"'
        ) % {
            'first_name': new_person.first_name,
            'last_name': new_person.last_name
        }
        email_addresses = set(entity.author_email
                              for entity in [new_person] + new_notes
                              if getattr(entity, 'author_email', ''))
        for address in email_addresses:
            self.send_mail(
                subject=subject,
                to=address,
                body=self.render_to_string(
                    'restoration_email.txt',
                    first_name=new_person.first_name,
                    last_name=new_person.last_name,
                    record_url=record_url
                )
            )

        self.redirect(record_url)
        
    def get_tombstone_and_verify_params(self):
        """Checks the request for a valid tombstone id and still valid
        crypto token. Returns a tuple containing:
        
            (tombstone or None, token or None, None or error string)
            
        If there is an error then tombstone will be None, and vice versa."""
        tombstone = model.PersonTombstone.get_by_key_name(self.params.id)
        if not tombstone:
            error = 'The record with the following ID no longer exists: %s' % \
                self.params.id.split(':', 1)[1]
            return (None, None, error)
        token = self.request.get('token')
        data = 'restore:%s' % self.params.id
        if not reveal.verify(data, token):
            return (None, None, 'Invalid token')
        return (tombstone, token, None)


if __name__ == '__main__':
    utils.run(('/restore', Restore))
