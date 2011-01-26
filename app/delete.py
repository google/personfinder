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

# The length of time a tombstone will exist before the ClearTombstones
# cron job will remove it from the database. Deletion reversals can only
# happen while a tombstone still exists.
TOMBSTONE_TTL_DAYS = 3 # days


def get_entities_to_delete(person):
    """Gather all the entities that are attached to this person."""
    entities = [person] + person.get_notes()
    if person.photo_url and person.photo_url.startswith('/photo?id='):
        photo = model.Photo.get_by_id(int(person.photo_url.split('=', 1)[1]))
        if photo:
            entities.append(photo)
    return entities


class Delete(utils.Handler):
    """Delete a person and dependent entities."""
    def get(self):
        """Prompt the user with a captcha to carry out the deletion."""
        person = model.Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        self.render('templates/delete.html', person=person,
                    entities=get_entities_to_delete(person),
                    view_url=self.get_url('/view', id=self.params.id),
                    captcha_html=self.get_captcha_html())

    def post(self):
        """If the captcha is valid, create tombstones for a delayed deletion.
        Otherwise, prompt the user with a new captcha."""
        person = model.Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        captcha_response = self.get_captcha_response()
        if self.is_test_mode() or captcha_response.is_valid:
            entities_to_delete = get_entities_to_delete(person)
            to_delete = []
            tombstones = []
            for e in entities_to_delete:
                if not isinstance(e, model.Photo):
                    to_delete.append(e)
                    tombstones.append(e.create_tombstone())

            # Create tombstones for people and notes. Photos are left as is.
            db.put(tombstones)
            # Delete all people and notes being replaced by tombstones. This
            # will remove the records from the search index and feeds, but
            # the creation of the tombstones will allow for an "undo".
            db.delete(to_delete)

            # Get all the e-mail addresses to notify.
            email_addresses = set(e.author_email for e in entities_to_delete
                                  if getattr(e, 'author_email', ''))
            # The app is only permitted to send e-mail from addresses of the
            # form <foo@app-id.appspotmail.com>.
            sender = 'do-not-reply@' + self.env.parent_domain.replace(
                'appspot.com', 'appspotmail.com')

            # i18n: Subject line of an e-mail message notifying a user
            # i18n: that a person record has been deleted
            subject=_(
                '[Person Finder] Deletion notice for '
                '%(first_name)s %(last_name)s'
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
                        days_until_deletion=TOMBSTONE_TTL_DAYS,
                        restore_url=self.get_restore_url(person)
                    )
                )

            # Log the deletion.
            reason_for_deletion = self.request.get('reason_for_deletion')
            model.PersonFlag(subdomain=self.subdomain, time=utils.get_utcnow(),
                             reason_for_report=reason_for_deletion,
                             is_delete=True).put()
            return self.error(200, _('The record has been deleted.'))
        else:
            captcha_html = self.get_captcha_html(captcha_response.error_code)
            self.render('templates/delete.html', person=person,
                        entities=get_entities_to_delete(person),
                        view_url=self.get_url('/view', id=self.params.id),
                        captcha_html=captcha_html)

    def get_restore_url(self, person, ttl=259200):
        """Returns a URL to be used for reversing the deletion of person. The
        default TTL for a URL is 3 days (259200 seconds)."""
        key_name = person.key().name()
        data = 'restore:%s' % key_name 
        token = reveal.sign(data, ttl) # 3 days in seconds
        return self.get_url('/restore', token=token, id=key_name)


if __name__ == '__main__':
    utils.run(('/delete', Delete))
