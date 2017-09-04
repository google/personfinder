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

import reveal

import model
import utils
from model import db

from django.utils.translation import ugettext as _


def get_enable_notes_url(handler, person, ttl=3*24*3600):
    """Returns a URL to be used for disabling comments to a person record."""
    key_name = person.key().name()
    data = 'enable_notes:%s' % key_name
    token = reveal.sign(data, ttl)
    return handler.get_url('/confirm_enable_notes',
                           token=token, id=key_name)


class Handler(utils.BaseHandler):
    """Handles an author request to disable comments to a person record."""

    def get(self):
        """Prompts the user with a CAPTCHA before proceeding the request."""
        person = model.Person.get(self.repo, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        self.render('enable_notes.html',
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
            enable_notes_url = get_enable_notes_url(self, person)
            utils.send_confirmation_email_to_record_author(self,
                                                           person,
                                                           "enable",
                                                           enable_notes_url,
                                                           self.params.id)

            return self.info(
                200, _('If you are the author of this note, please check your '
                       'e-mail for a link to confirm that you want to enable '
                       'notes on this record.  Otherwise, please wait for the '
                       'record author to confirm your request.'))
        else:
            captcha_html = self.get_captcha_html(captcha_response.error_code)
            self.render('enable_notes.html',
                        person=person,
                        view_url=self.get_url('/view', id=self.params.id),
                        captcha_html=captcha_html)
