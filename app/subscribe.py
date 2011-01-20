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

from django.utils.html import escape

from google.appengine.api import taskqueue
from google.appengine.api.taskqueue import Task
from google.appengine.ext import db

from model import Person
from utils import *

import model
import reveal

def send_notifications(person, note, handler):
    """Sends status updates about the person"""
    # sender address for the server must be of the following form to get 
    # permission to send emails: foo@app-id.appspotmail.com
    # Here, the domain is automatically retrieved and altered as appropriate.
    sender_domain = handler.env.parent_domain.replace('appspot.com', 
                                                   'appspotmail.com')
    sender='Do Not Reply <do-not-reply@%s>' % sender_domain
    subject = _('Person Finder: Status update for %(given_name)s' +
                ' %(family_name)s') % {'given_name': person.first_name, 
                                       'family_name': person.last_name}
    location = note.last_known_location and\
        _("Last known location: %s") % note.last_known_location or '' 
    
    #send messages
    for subscribed_person in person.subscribed_persons:
        if (model.is_valid_email(subscribed_person)):
            data = 'unsubscribe:%s' % subscribed_person
            token = reveal.sign(data, 604800) # valid for one week (in seconds)
            link = handler.get_url('/unsubscribe', token=token,
                                 email=subscribed_person, id=person.record_id)
            body = _(
"""A user has updated the status for a missing person at %(domain)s.
Status of this person: %(status)s
Personally talked with the person AFTER the disaster: %(is_talked)s
%(location)s
Message:
%(content)s


You can view the full record at %(view_url)s

--
You received this notification because you are subscribed. 
To unsubscribe, copy this link to your browser and press Enter:\n
%(unsubscribe_link)s""") % {'domain': handler.env.domain,
                          'status': _('Unknown') if note.status == ''\
                                                 else note._status,
                          'is_talked': _('No') if note.found == False \
                                               else _('Yes'),
                          'location': location, 
                          'content': note._text,
                          'view_url': handler.get_url('/view', 
                                                      id=person.record_id),
                          'unsubscribe_link' : link}

            # Add the task to the email-throttle queue
            task = Task(params={'sender': sender,
                                'subject': subject,
                                'to': subscribed_person,
                                'body': body
                                })
            task.add(queue_name='email-throttle', transactional=False) 

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
                '%(family_name)s') % {'given_name': person.first_name,
                                       'family_name': person.last_name}     

    data = 'unsubscribe:%s' % email
    token = reveal.sign(data, 604800) # valid for one week (in seconds)
    link = handler.get_url('/unsubscribe', token=token, email=email, 
                           id=person.record_id)
    body = _("""
You have subscribed to status updates for a missing person at %(domain)s.

You can view the full profile at %(view_url)s


To unsubscribe, copy this link to your browser and press Enter:
%(unsubscribe_link)s""") % {'domain': handler.env.domain,
                            'view_url': handler.get_url('/view', 
                                                        id=person.record_id),
                            'unsubscribe_link': link}

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
        captcha_html = get_captcha_html()
        form_action = self.get_url('/subscribe', id=self.params.id)
        back_url = self.get_url('/view', id=self.params.id)
        
        person = Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)
        
        self.render('templates/subscribe_captcha.html', 
                    params=self.params,
                    captcha_html=captcha_html,
                    email_subscr=self.params.email_subscr or '',
                    form_action=form_action,
                    back_url=back_url,
                    first_name=person.first_name,
                    last_name=person.last_name)

    def post(self):
        person = Person.get(self.subdomain, self.params.id)

        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        result = person.add_subscriber(self.params.email_subscr)

        if result == False:
            # Invalid email
            captcha_html = get_captcha_html()
            form_action = self.get_url('/subscribe', id=self.params.id)
            return self.render('templates/subscribe_captcha.html',
                    params=self.params,
                    email_subscr=self.params.email_subscr,
                    message=_('Invalid e-mail address. Please try again.'),
                    captcha_html=captcha_html,
                    form_action=form_action)

        if result is None:
            # User is already subscribed
            url = self.get_url('/view', id=self.params.id)
            link_text = _('Return to the record for %s %s.' ) % (
                           escape(person.first_name), escape(person.last_name))
            html = '<a href="%s">%s</a>' % (url, link_text)
            message_html = _('Your are already subscribed. ' + html)
            return self.info(200, message_html=message_html)

        # Email must be valid, check the captcha
        captcha_response = get_captcha_response(self.request)
        if not captcha_response.is_valid and not self.is_test_mode():
            # Captcha is incorrect
            captcha_html = get_captcha_html(captcha_response.error_code)
            form_action = self.get_url('/subscribe', id=self.params.id)                
            return self.render('templates/subscribe_captcha.html',
                                params=self.params,
                                email_subscr=self.params.email_subscr,                                
                                captcha_html=captcha_html,
                                form_action=form_action)

        # Captcha and email are correct
        db.put(person)
        send_subscription_confirmation(self, person,
                                    self.params.email_subscr)
        url = self.get_url('/view', id=self.params.id)
        link_text = _('Return to the record for %s %s.' ) % (
                           escape(person.first_name), escape(person.last_name))
        html = '<a href="%s">%s</a>' % (url, link_text)
        message_html = _('Your are successfully subscribed. ' + html)                  
        return self.info(200, message_html=message_html)

if __name__ == '__main__':
    run(('/subscribe', Subscribe))