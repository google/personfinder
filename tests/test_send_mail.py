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

"""Tests for send_mail.py."""

from google.appengine.api import mail
from google.appengine.api import mail_errors
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import logging
import model
import mox
import os
import send_mail
import test_handler
import unittest
import webob

class SendMailTests(unittest.TestCase):
    '''Test the send_mail error handling.'''

    def test_email_fail(self):
        subject = 'test'
        to = 'bad_email_address'
        sender = 'me@example.com'
        body = 'stuff'
        mymox = mox.Mox()
        mymox.StubOutWithMock(logging, 'error')
        logging.error('EmailSender (to: %s, subject: %s), '
                      'failed with exception %s' % (to, subject, 'exception'))
        mymox.StubOutWithMock(mail, 'send_mail')
        mail.send_mail(sender=sender,
                       subject=subject,
                       to=to,
                       body=body).AndRaise(mail_errors.Error('exception'))
        handler = send_mail.EmailSender()
        repo = 'haiti'
        model.Repo(key_name=repo).put()
        request = webapp.Request(
            webob.Request.blank(
                '/admin/send_mail?to=%s&subject=%s&sender=%s' %
                (to, subject, sender)).environ)
        request.method = 'POST'
        request.body = 'body=%s' % body
        handler.initialize(request, webapp.Response())
        mymox.ReplayAll()
        handler.post()
        # shouldn't raise an error.
        assert True
        mymox.VerifyAll()
