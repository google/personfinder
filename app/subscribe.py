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

from google.appengine.ext import db
from google.appengine.api import taskqueue

import model
import reveal
from utils import *

from django.utils.html import escape
from django.utils.translation import ugettext as _

EMAIL_PATTERN = re.compile(r'(?:^|\s)[-a-z0-9_.%$+]+@(?:[-a-z0-9]+\.)+'
                           '[a-z]{2,6}(?:\s|$)', re.IGNORECASE)

def is_email_valid(email):
    """Validates an email address, returning True on correct,
    False on incorrect, None on empty string."""
    # Note that google.appengine.api.mail.is_email_valid() is unhelpful;
    # it checks only for the empty string
    if not email:
        return None
    if EMAIL_PATTERN.match(email):
        return True
    else:
        return False


def get_unsubscribe_link(handler, person, email, ttl=7*24*3600):
    """Returns a link that will remove the given email address from the list
    of subscribers for the given person, default ttl is one week"""
    data = 'unsubscribe:%s' % email
    token = reveal.sign(data, ttl)
    return handler.get_url('/unsubscribe', token=token, email=email,
                           id=person.record_id)

def get_sender(handler):
    """Return the default sender of subscribe emails."""
    # Sender address for the server must be of the following form to get
    # permission to send emails: foo@app-id.appspotmail.com
    # Here, the domain is automatically retrieved and altered as appropriate.
    # TODO(kpy) Factor this out of subscribe
    domain = handler.env.parent_domain.replace('appspot.com', 'appspotmail.com')
    return 'Do Not Reply <do-not-reply@%s>' % domain

def send_notifications(person, note, handler):
    """Sends status updates about the person"""
    sender=get_sender(handler)
    #send messages
    for sub in person.get_subscriptions():
        if is_email_valid(sub.email):
            django.utils.translation.activate(sub.language)
            subject = _('Person Finder: Status update for %(given_name)s '
                        '%(family_name)s') % {
                            'given_name': escape(person.first_name),
                            'family_name': escape(person.last_name)}
            body = handler.render_to_string(
                'person_status_update_email.txt',
                first_name=person.first_name,
                last_name=person.last_name,
                note=note,
                note_status_text=get_note_status_text(note),
                site_url=handler.get_url('/'),
                view_url=handler.get_url('/view', id=person.record_id),
                unsubscribe_link=get_unsubscribe_link(handler, person,
                                                      sub.email))
            taskqueue.add(queue_name='send-mail', url='/admin/send_mail',
                          params={'sender': sender,
                                  'to': sub.email,
                                  'subject': subject,
                                  'body': body})
    django.utils.translation.activate(handler.env.lang)

def send_subscription_confirmation(handler, person, email):
    """Sends subscription confirmation when person subscribes to
    status updates"""
    subject = _('Person Finder: You are subscribed to status updates for ' +
                '%(given_name)s %(family_name)s') % {
                    'given_name': escape(person.first_name),
                    'family_name': escape(person.last_name)}
    body = handler.render_to_string(
        'subscription_confirmation_email.txt',
        first_name=person.first_name,
        last_name=person.last_name,
        site_url=handler.get_url('/'),
        view_url=handler.get_url('/view', id=person.record_id),
        unsubscribe_link=get_unsubscribe_link(handler, person, email))
    taskqueue.add(queue_name='send-mail', url='/admin/send_mail',
                  params={'sender': get_sender(handler),
                          'to': email,
                          'subject': subject,
                          'body': body})

class Subscribe(Handler):
    """Handles requests to subscribe to notifications on Person and
    Note record updates."""
    def get(self):
        person = model.Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        form_action = self.get_url('/subscribe', id=self.params.id)
        back_url = self.get_url('/view', id=self.params.id)
        self.render('templates/subscribe_captcha.html',
                    person=person,
                    captcha_html=self.get_captcha_html(),
                    subscribe_email=self.params.subscribe_email or '',
                    form_action=form_action,
                    back_url=back_url,
                    first_name=person.first_name,
                    last_name=person.last_name)

    def post(self):
        person = model.Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        if not is_email_valid(self.params.subscribe_email):
            # Invalid email
            captcha_html = self.get_captcha_html()
            form_action = self.get_url('/subscribe', id=self.params.id)
            return self.render('templates/subscribe_captcha.html',
                               person=person,
                               subscribe_email=self.params.subscribe_email,
                               message=_(
                                   'Invalid e-mail address. Please try again.'),
                               captcha_html=captcha_html,
                               form_action=form_action)

        existing = model.Subscription.get(self.subdomain, self.params.id,
                                          self.params.subscribe_email)
        if existing and existing.language == self.env.lang:
            # User is already subscribed
            url = self.get_url('/view', id=self.params.id)
            link_text = _('Return to the record for %(given_name)s '
                          '%(family_name)s.') % {
                              'given_name': escape(person.first_name),
                              'family_name': escape(person.last_name)}
            html = '<a href="%s">%s</a>' % (url, link_text)
            message_html = _('You are already subscribed. ' + html)
            return self.info(200, message_html=message_html)

        # Check the captcha
        captcha_response = self.get_captcha_response()
        if not captcha_response.is_valid and not self.is_test_mode():
            # Captcha is incorrect
            captcha_html = self.get_captcha_html(captcha_response.error_code)
            form_action = self.get_url('/subscribe', id=self.params.id)
            return self.render('templates/subscribe_captcha.html',
                               person=person,
                               subscribe_email=self.params.subscribe_email,
                               captcha_html=captcha_html,
                               form_action=form_action)

        if existing:
            subscription = existing
            subscription.language = self.env.lang
        else:
            subscription = model.Subscription.create(
                self.subdomain, self.params.id, self.params.subscribe_email,
                self.env.lang)
        db.put(subscription)
        send_subscription_confirmation(self, person,
                                       self.params.subscribe_email)
        url = self.get_url('/view', id=self.params.id)
        link_text = _('Return to the record for %(given_name)s '
                      '%(family_name)s') % {
                          'given_name': escape(person.first_name),
                          'family_name': escape(person.last_name)}
        html = ' <a href="%s">%s</a>' % (url, link_text)
        message_html = _('You are successfully subscribed.') + html
        return self.info(200, message_html=message_html)

if __name__ == '__main__':
    run(('/subscribe', Subscribe))
