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
from utils import datetime
import model
import reveal
import utils


import urllib
urllib.getproxies_macosx_sysconf = lambda: {}

class ReverseDelete(utils.Handler):
    def get(self):
        """Prompts a user with a CAPTCHA to re-instate the supplied record.
        There must be a valid token supplied as post param "token"."""
        tombstone, token, error = self.get_tombstone_and_verify_params()
        if error:
            return self.error(400, error)

        captcha_html = utils.get_captcha_html()
        self.render('templates/reverse_delete.html',
                    captcha_html=captcha_html, token=token, id=self.params.id)

    def post(self):
        """If the submitted CAPTCHA is valid, re-instates the record and
        removes the tombstone. Otherwise, display another CAPTCHA to the
        user for authentication."""
        tombstone, token, error = self.get_tombstone_and_verify_params()
        if error:
            return self.error(400, error)

        captcha_response = utils.get_captcha_response(self.request)
        if not captcha_response.is_valid and not self.is_test_mode():
            captcha_html = utils.get_captcha_html(captcha_response.error_code)
            self.render('templates/reverse_delete.html',
                        captcha_html=captcha_html, token=token, id=self.params.id)
            return

        person_props = model.get_properties_as_dict(tombstone)
        person_props.update(entry_date=datetime.now())
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
        model.PersonFlag(subdomain=tombstone.subdomain, time=datetime.utcnow(),
                         is_delete=False).put()

        sender_domain = self.env.parent_domain.replace(
            'appspot.com', 'appspotmail.com')
        record_url = self.get_url(
            '/view', id=new_person.record_id, subdomain=new_person.subdomain)
        message = mail.EmailMessage(
            sender='Do Not Reply<do-not-reply@%s>' % sender_domain,
            subject=_('[Person Finder] Record recreation notice for ' +
                      '%(given_name)s %(family_name)s'
            ) % {'given_name': new_person.first_name,
                 'family_name': new_person.last_name},
            body=_('''
The record for %(given_name)s %(family_name)s has been recreated. To view the record, follow this link:

    %(record_url)s
''') % {'given_name': new_person.first_name,
        'family_name': new_person.last_name,
        'record_url': record_url})

        email_addresses = set(e.author_email for e in new_notes + [new_person]
                              if getattr(e, 'author_email', ''))
        for address in email_addresses:
            message.to = address
            message.send()

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
        data = 'reverse_delete:%s' % self.params.id
        if not reveal.verify(data, token):
            return (None, None, 'Invalid token')
        return (tombstone, token, None)


if __name__ == '__main__':
    utils.run(('/reverse_delete', ReverseDelete))
