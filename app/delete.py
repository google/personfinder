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

import os
import prefix
import reveal
import string
import sys

from google.appengine.api import mail
from recaptcha.client import captcha

import config
import model
import utils
from model import db
from utils import datetime


def get_entities_to_delete(person):
    # Gather all the entities that are attached to this person.
    entities = [person] + person.get_notes()
    if person.photo_url and person.photo_url.startswith('/photo?id='):
        photo = model.Photo.get_by_id(int(person.photo_url.split('=', 1)[1]))
        if photo:
            entities.append(photo)
    return entities


class Delete(utils.Handler):
    def get(self):
        """Prompt the user with a captcha to carry out the deletion."""
        person = model.Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)
        captcha_html = utils.get_captcha_html()

        self.render('templates/delete.html', person=person,
                    entities=get_entities_to_delete(person),
                    view_url=self.get_url('/view', id=self.params.id),
                    save_url=self.get_url('/api/read', id=self.params.id),
                    captcha_html=captcha_html)

    def post(self):
        """If the captcha is valid, carry out the deletion. Otherwise, prompt
        the user with a new captcha."""
        person = model.Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        captcha_response = utils.get_captcha_response(self.request)
        if self.is_test_mode() or captcha_response.is_valid:
            entities_to_delete = get_entities_to_delete(person)
            email_addresses = set(e.author_email for e in entities_to_delete
                                  if getattr(e, 'author_email', ''))
            # Sender address for the server must be of the following form to
            # get permission to send emails: foo@app-id.appspotmail.com .
            # Here, the domain is automatically retrieved and altered as
            # appropriate.
            sender_domain = self.env.parent_domain.replace(
                'appspot.com', 'appspotmail.com')
            # i18n: Body text of an e-mail message that gives the user
            # i18n: a link to delete a record
            body = string.Template(_('''
A user has deleted the record for a missing person at %(domain_name)s.

$identifying_text, so we are contacting
you to inform you of the deletion. If you feel this action was a mistake,
you can re-create the record by visiting the following website:

    %(site_url)s
''') % {'domain_name': self.env.domain,
        'site_url': self.get_url('/')})
            person_author_body = body.substitute(
                # i18n: Identifying text for the author of a record
                identifying_text=_('You are the author of this record'))
            note_author_body = body.substitute(
                # i18n: Identifying text for the author of a note
                identifying_text=_('You added a note to this record'))
            message = mail.EmailMessage(
                sender='Do Not Reply <do-not-reply@%s>' % sender_domain,
                # i18n: Subject line of an e-mail message that gives the
                # i18n: user a link to delete a record
                subject=_(
                    'Deletion notification for %(given_name)s %(family_name)s'
                ) % {'given_name': person.first_name,
                     'family_name': person.last_name}
            )
            db.delete(entities_to_delete)
            for email in email_addresses:
                message.body = email == person.author_email and \
                    person_author_body or note_author_body
                message.to = email
                message.send()

            # Track when deletions occur
            reason_for_deletion = self.request.get('reason_for_deletion')
            model.PersonFlag(subdomain=self.subdomain, time=datetime.utcnow(),
                             reason_for_deletion=reason_for_deletion).put()
            return self.error(200, _('The record has been deleted.'))
        else:
            captcha_html = utils.get_captcha_html(captcha_response.error_code)
            self.render('templates/delete.html', person=person,
                        entities=get_entities_to_delete(person),
                        view_url=self.get_url('/view', id=self.params.id),
                        save_url=self.get_url('/api/read', id=self.params.id),
                        captcha_html=captcha_html)


if __name__ == '__main__':
    utils.run(('/delete', Delete))
