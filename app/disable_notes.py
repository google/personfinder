#!/usr/bin/python2.7
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

import logging

import reveal

import model
import utils
from google.appengine.ext import db

from django.utils.translation import ugettext as _


def get_disable_notes_url(handler, person, ttl=3*24*3600):
    """Returns a URL to be used for disabling notes to a person record."""
    key_name = person.key().name()
    data = 'disable_notes:%s' % key_name
    token = reveal.sign(data, ttl)
    return handler.get_url('/confirm_disable_notes',
                           token=token, id=key_name)


class Handler(utils.BaseHandler):
    """Handles an author request to disable notes to a person record."""

    def get(self):
        """Prompts the user with a CAPTCHA before proceeding the request."""
        person = model.Person.get(self.repo, self.params.id)
        if not person:
            # Place holder name here is id_str, not id, because
            # the translation system doesn't allow the same string in both
            # a place holder name and a normal uppercase word in one message.
            return self.error(
                400,
                _('No person with ID: %(id_str)s.')
                % {'id_str': self.params.id})

        self.render('disable_notes.html',
                    person=person,
                    view_url=self.get_url('/view', id=self.params.id),
                    captcha_html=self.get_captcha_html())

    def post(self):
        """If the user passed the CAPTCHA, send the confirmation email."""
        person = model.Person.get(self.repo, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        captcha_response = self.get_captcha_response()
        if captcha_response.is_valid:
            disable_notes_url = get_disable_notes_url(self, person)
            # To make debug with local dev_appserver easier.
            logging.info('Disable notes URL: %s' % disable_notes_url)
            utils.send_confirmation_email_to_record_author(self,
                                                           person,
                                                           "disable",
                                                           disable_notes_url,
                                                           self.params.id)

            return self.info(
                200, _('If you are the author of this note, please check your '
                       'e-mail for a link to confirm that you want to disable '
                       'notes on this record.  Otherwise, please wait for the '
                       'record author to confirm your request.'))
        else:
            captcha_html = self.get_captcha_html(captcha_response.error_code)
            self.render('disable_notes.html',
                        person=person,
                        view_url=self.get_url('/view', id=self.params.id),
                        captcha_html=captcha_html)
