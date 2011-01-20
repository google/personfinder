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
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class EmailSender(webapp.RequestHandler):
    """Simple servlet to send email; intended to be called from a taskqueue
    task so email sending can be throttled to stay below app engine quotas."""
    def post(self):
        sender = self.request.get('sender')
        subject = self.request.get('subject')
        to = self.request.get('to')
        body = self.request.get('body')
         
        if sender is not None and subject is not None\
                 and to is not None and body is not None:
            message = mail.EmailMessage(sender=sender, 
                                        subject=subject, to=to, body=body)
            message.send()


def main():
    run_wsgi_app(webapp.WSGIApplication([
        ('/_ah/queue/email-throttle', EmailSender),
    ]))

if __name__ == '__main__':
    main()    