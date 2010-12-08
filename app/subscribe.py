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
from google.appengine.api import taskqueue
from google.appengine.api.taskqueue import Task
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import reveal

def send_notifications(person, note, view):
    """Sends status updates about the person"""
    # sender address for the server must be of the following form to get 
    # permission to send emails: foo@app-id.appspotmail.com
    # Here, the domain is automatically retrieved and altered as appropriate.
    sender_domain = view.env.parent_domain.replace('appspot.com', 'appspotmail.com')
    sender='Do Not Reply <do-not-reply@%s>' % sender_domain
    subject = 'Person Finder: Status update for %(given_name)s %(family_name)s' % {'given_name': person.first_name, 'family_name': person.last_name}
    location = "" if note.last_known_location == '' else "Last known location: %s" % note.last_known_location 
                              
    #send messages
    for subscribed_person in person.subscribed_persons:
        if (subscribed_person.strip() != ""):
            verify = reveal.sign(subscribed_person)
            content = view.params.id
            link = reveal.make_reveal_url(view, content)
            link += "&action=unsubscribe&email="+subscribed_person+"&verify="+verify 
            body = """
A user has updated the status for a missing person at %(domain)s.
Status of this person: %(status)s
Personally talked with the person AFTER the disaster: %(is_talked)s
%(location)s
Message:
$(content)s


You can view the full record at $(record_url)s


You received this notification because you are subscribed. To unsubscribe, copy
this link to your browser and press Enter:
$(unsubscribe_link)s""" % {'domain': view.env.domain,
                          'status': 'Unknown' if note._status == '' else note._status,
                          'is_talked': 'No' if note.found == False else 'Yes',
                          'location': location, 
                          'content': note._text,
                          'record_url': person._source_url,
                          'unsubscribe_link' : link}

            # Add the task to the email-throttle queue
            task = Task(params={'sender': sender,
                                'subject': subject,
                                'to': subscribed_person,
                                'body': body
                                })
            task.add(queue_name='email-throttle', transactional=False) 
            
            
            
class EmailSender(webapp.RequestHandler):
    def post(self):
         sender = self.request.get('sender')
         subject = self.request.get('subject')
         to = self.request.get('to')
         body = self.request.get('body')
         
         if sender is not None and subject is not None and to is not None and body is not None:
             message = mail.EmailMessage(sender=sender, subject=subject, to=to, body=body)
             message.send()

def main():
    run_wsgi_app(webapp.WSGIApplication([
        ('/_ah/queue/email-throttle', EmailSender),
    ]))

if __name__ == '__main__':
    main()         