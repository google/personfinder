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

from model import Person
from utils import *

import model
import reveal

class Subscribe(Handler):
    def get(self):        
        captcha_html = get_captcha_html()
        form_action = self.get_url(
            '/subscribe', id=self.params.id)
        self.render('templates/subscribe_captcha.html', 
                    params=self.params,                                         
                    captcha_html=captcha_html,
                    email_subscr=self.params.email_subscr or '',
                    form_action=form_action)   
    def post(self):        
        person = Person.get(self.subdomain, self.params.id)
        if person:
            result = person.add_subscriber(self.params.email_subscr)                
            if result == False:
                captcha_html = get_captcha_html()
                form_action = self.get_url(
                '/subscribe', id=self.params.id)                   
                self.render('templates/subscribe_captcha.html', 
                        params=self.params,
                        email_subscr=self.params.email_subscr,
                        captcha_error_field=_('Invalid e-mail address. ' +  
                                              'Please try again.'),
                        captcha_html=captcha_html,
                        form_action=form_action)
            elif result == True:                
                captcha_response = get_captcha_response(self.request)                        
                if (captcha_response.is_valid == False): 
                    captcha_html = get_captcha_html()
                    form_action = self.get_url(
                                '/subscribe', id=self.params.id)                   
                    self.render('templates/subscribe_captcha.html', 
                                params=self.params,
                                email_subscr=self.params.email_subscr,
                                captcha_error_field=_('You entered two words '
                                            'incorrectly. Please try again.'),
                                captcha_html=captcha_html,
                                form_action=form_action)
                else:
                    db.put(person)
                    send_subscription_confirmation(self, person,
                                                self.params.email_subscr)
                    url = self.get_url(
                                       '/view', id=self.params.id)
                    here_word = _('here')
                    html = '<a href="%s">%s</a>' % (url, here_word)
                    message_html = _('Your are successfully subscribed. '
                                     'Please click %s to return.') % html                   
                    return self.info(200, message_html=message_html)
            else:
                url = self.get_url('/view', id=self.params.id)
                here = _('here')
                html = '<a href="%s">%s</a>' % (url, here)
                message_html = _('Your are already subscribed. '
                                 'Please click %s to return.') % html                   
                return self.info(200, message_html=message_html)
                

def send_notifications(person, note, view):
    """Sends status updates about the person"""
    # sender address for the server must be of the following form to get 
    # permission to send emails: foo@app-id.appspotmail.com
    # Here, the domain is automatically retrieved and altered as appropriate.
    sender_domain = view.env.parent_domain.replace('appspot.com', 
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
            link = view.get_url('/unsubscribe', token=token,
                                 email=subscribed_person, id=person.record_id)
            body = _(
"""A user has updated the status for a missing person at %(domain)s.
Status of this person: %(status)s
Personally talked with the person AFTER the disaster: %(is_talked)s
%(location)s
Message:
%(content)s


You can view the full record at %(record_url)s

--
You received this notification because you are subscribed. 
To unsubscribe, copy this link to your browser and press Enter:\n
%(unsubscribe_link)s""") % {'domain': view.env.domain,
                          'status': _('Unknown') if note.status == ''\
                                              else note._status,
                          'is_talked': _('No') if note.found == False \
                                               else _('Yes'),
                          'location': location, 
                          'content': note._text,
                          'record_url': person.person_record_id,
                          'unsubscribe_link' : link}
            
            # Add the task to the email-throttle queue
            task = Task(params={'sender': sender,
                                'subject': subject,
                                'to': subscribed_person,
                                'body': body
                                })
            task.add(queue_name='email-throttle', transactional=False) 

def send_subscription_confirmation(view, person, email):
    """Sends subscription confirmation when person subscribes to 
    status updates"""
    # sender address for the server must be of the following form to get 
    # permission to send emails: foo@app-id.appspotmail.com
    # Here, the domain is automatically retrieved and altered as appropriate.
    sender_domain = view.env.parent_domain.replace('appspot.com', 
                                                   'appspotmail.com')
    sender='Do Not Reply <do-not-reply@%s>' % sender_domain
    subject = _('Person Finder: You are subscribed to status updates for '+
                '%(given_name)s '+
                '%(family_name)s') % {'given_name': person.first_name,
                                       'family_name': person.last_name}     
    
    data = 'unsubscribe:%s' % email
    token = reveal.sign(data, 604800) # valid for one week (in seconds)
    link = view.get_url('/unsubscribe', token=token,
                                 email=email, id=person.record_id)
    body = _("""
You have subscribed to status updates for a missing person at %(domain)s.

You can view the full profile at %(record_url)s


To unsubscribe, copy this link to your browser and press Enter:
%(unsubscribe_link)s""") % {'domain': view.env.domain,                          
                          'record_url': person.person_record_id,
                          'unsubscribe_link' : link}
            
    # Add the task to the email-throttle queue
    task = Task(params={'to': email,
                        'sender': sender,
                        'subject': subject,                       
                        'body': body
                        })
    task.add(queue_name='email-throttle', transactional=False) 

if __name__ == '__main__':
    run(('/subscribe', Subscribe))