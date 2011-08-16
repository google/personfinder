#!/usr/bin/python2.5
# Copyright 2011 Google Inc.
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

import datetime
import reveal

import model
import utils
from model import db

from django.utils.translation import ugettext as _

# The number of days we extend a record, by default.
EXPIRED_EXTENSION_DAYS = 60

def get_extension_days(handler):
    return handler.config.default_extension_days or EXPIRED_EXTENSION_DAYS
    

class Handler(utils.BaseHandler):
    """Handles a user request to extend expiration of a person record."""

    def show_page(self, person, error_code=None): 
        self.render('templates/extend.html',
                    person=person,
                    view_url=self.get_url('/view', id=self.params.id),
                    captcha_html=self.get_captcha_html(error_code=error_code))
        
    def get(self):
        """Prompts the user with a Turing test before carrying out extension."""
        person = model.Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)
        self.show_page(person)

    def post(self):
        """If the user passed the Turing test, extend the record."""
        person = model.Person.get(self.subdomain, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        captcha_response = self.get_captcha_response()
        if self.is_test_mode() or captcha_response.is_valid:
            # Log the user action.
            if person.is_original():
                model.UserActionLog.put_new('extend', person)
                # For an original record, set the expiry date.
                # Set the expiry_date to now, and set is_expired flags to match.
                person.expiry_date = person.expiry_date + datetime.timedelta(
                    get_extension_days(self))
                # put_expiry_flags will only save if the status changed, so
                # we save here too.
                person.put() 
                person.put_expiry_flags()
                view_url=self.get_url('/view', id=person.record_id)
                return self.info(
                    200,
                    _('The record has been extended to %(expiry_date)s.') % 
                      {'expiry_date': self.to_local_time(
                            person.expiry_date).strftime('%Y-%m-%d')},
                    message_html='&nbsp;<a href=\'' + view_url +
                    '\'>' + _('View the record') + '</a>')
            else: 
                # this shouldn't happen in normal work flow.
                return self.info(200, _('The record cannot be extended.',))
        else:
            self.show_page(person, captcha_response.error_code)
