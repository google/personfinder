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

from google.appengine.api import taskqueue
from google.appengine.api.taskqueue import Task
from google.appengine.ext import db

import model
import reveal
from utils import *

from django.utils.html import escape
from django.utils.translation import ugettext as _

def get_unsubscribe_link(handler, person, email, ttl=604800):
    """Returns a link to unsubscribe, defautlt ttl is one week"""
    data = 'unsubscribe:%s' % email
    token = reveal.sign(data, ttl)
    return handler.get_url('/unsubscribe', token=token, email=email,
                           id=person.record_id)

def send_notifications(person, note, handler):
    """Sends status updates about the person"""
    # sender address for the server must be of the following form to get
    # permission to send emails: foo@app-id.appspotmail.com
    # Here, the domain is automatically retrieved and altered as appropriate.
    sender_domain = handler.env.parent_domain.replace('appspot.com',
                                                      'appspotmail.com')
    sender='Do Not Reply <do-not-reply@%s>' % sender_domain

    #send messages
    for lang, email in person.get_subscribers():
        django.utils.translation.activate(lang)
        subject = _('Person Finder: Status update for %(given_name)s '
                    '%(family_name)s') % {
                        'given_name': escape(person.first_name),
                        'family_name': escape(person.last_name)}
        unsubscribe_link = get_unsubscribe_link(handler, person, email)
        if (model.is_valid_email(email)):
            body = handler.render_to_string(
                'person_status_update_email.txt',
                first_name=person.first_name,
                last_name=person.last_name,
                note=note,
                note_status_text=get_note_status_text(note),
                site_url=handler.get_url('/'),
                view_url=handler.get_url('/view', id=person.record_id),
                unsubscribe_link=unsubscribe_link)

            # Add the task to the email-throttle queue
            task = Task(params={'sender': sender,
                                'subject': subject,
                                'to': email,
                                'body': body
                                })
            task.add(queue_name='email-throttle', transactional=False)
    django.utils.translation.activate(handler.params.lang)

def send_subscription_confirmation(handler, person, email):
    """Sends subscription confirmation when person subscribes to
    status updates"""
    # sender address for the server must be of the following form to get
    # permission to send emails: foo@app-id.appspotmail.com
    # Here, the domain is automatically retrieved and altered as appropriate.
    sender_domain = handler.env.parent_domain.replace('appspot.com',
                                                      'appspotmail.com')
    sender='Do Not Reply <do-not-reply@%s>' % sender_domain
    subject = _('Person Finder: You are subscribed to status updates for ' +
                '%(given_name)s ' +
                '%(family_name)s') % {'given_name': escape(person.first_name),
                                      'family_name': escape(person.last_name)}
    unsubscribe_link=get_unsubscribe_link(handler, person, email)
    body = handler.render_to_string(
        'subscription_confirmation_email.txt',
        first_name=person.first_name,
        last_name=person.last_name,
        site_url=handler.get_url('/'),
        view_url=handler.get_url('/view', id=person.record_id),
        unsubscribe_link=unsubscribe_link)

    # Add the task to the email-throttle queue
    task = Task(params={'to': email,
                        'sender': sender,
                        'subject': subject,
                        'body': body
                        })
    task.add(queue_name='email-throttle', transactional=False)

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

        result = person.add_subscriber(
            self.env.lang, self.params.subscribe_email)

        if result == False:
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

        if result is None:
            # User is already subscribed
            url = self.get_url('/view', id=self.params.id)
            link_text = _('Return to the record for %(given_name)s '
                          '%(family_name)s.') % {
                              'given_name': escape(person.first_name),
                              'family_name': escape(person.last_name)}
            html = '<a href="%s">%s</a>' % (url, link_text)
            message_html = _('Your are already subscribed. ' + html)
            return self.info(200, message_html=message_html)

        # Email must be valid, check the captcha
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

        # Captcha and email are correct
        db.put(person)
        send_subscription_confirmation(self, person,
                                       self.params.subscribe_email)
        url = self.get_url('/view', id=self.params.id)
        link_text = _('Return to the record for %(given_name)s '
                      '%(family_name)s') % {
                          'given_name': escape(person.first_name),
                          'family_name': escape(person.last_name)}
        html = ' <a href="%s">%s</a>' % (url, link_text)
        message_html = _('Your are successfully subscribed.') + html
        return self.info(200, message_html=message_html)

if __name__ == '__main__':
    run(('/subscribe', Subscribe))
