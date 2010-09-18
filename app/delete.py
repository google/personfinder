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

from datetime import datetime
from google.appengine.api import mail
from model import *
from utils import *
import prefix
import reveal
import sys


def get_entities_to_delete(person):
    # Gather all the entities that are attached to this person.
    entities = [person] + person.get_notes()
    if person.photo_url and person.photo_url.startswith('/photo?id='):
        photo = Photo.get_by_id(int(person.photo_url.split('=', 1)[1]))
        if photo:
            entities.append(photo)
    return entities


class Delete(Handler):
    def get(self):
        """If no signature is present, offer to send out a deletion code.
        If a signature is present, confirm deletion before carrying it out."""
        person = Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        self.render('templates/delete.html', person=person,
                    entities=get_entities_to_delete(person),
                    view_url=self.get_url('/view', id=self.params.id),
                    save_url=self.get_url('/api/read', id=self.params.id))

    def post(self):
        """If no signature is present, send out a deletion code.
        If a signature is present, carry out the deletion."""
        person = Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        action = ('delete', str(self.params.id))
        if self.params.signature:
            if reveal.verify(action, self.params.signature):
                db.delete(get_entities_to_delete(person))
                # i18n: Message telling the user that a record has been deleted.
                return self.error(200, _('The record has been deleted.'))
            else:
                # i18n: Message for an unauthorized attempt to delete a record.
                return self.error(403, _('The authorization code was invalid.'))
        else:
            mail.send_mail(
                sender='do not reply <do-not-reply@%s>' % self.env.domain,
                to='<%s>' % person.author_email,
                # i18n: Subject line of an e-mail message that gives the
                # i18n: user a link to delete a record
                subject=_(
                    'Deletion request for %(given_name)s %(family_name)s'
                ) % {'given_name': person.first_name,
                     'family_name': person.last_name},
                # i18n: Body text of an e-mail message that gives the user
                # i18n: a link to delete a record
                body = _('''
We have received a deletion request for a missing person record at
%(domain_name)s.

Your e-mail address was entered as the author of this record, so we
are contacting you to confirm whether you want to delete it.

To delete this record, use this link:

    %(delete_url)s

To view the record, use this link:

    %(view_url)s

''') % {'domain_name': self.env.domain,
        'delete_url': self.get_url('/delete', id=self.params.id,
                                   signature=reveal.sign(action, 24*3600)),
        'view_url': self.get_url('/view', id=self.params.id)}
            )

            # i18n: Message explaining to the user that the e-mail message
            # i18n: containing a link to delete a record has been sent out.
            return self.error(200, _('An e-mail message with a deletion code has been sent.  The code will expire in one day.'))

if __name__ == '__main__':
    run(('/delete', Delete))
