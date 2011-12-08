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
from model import Subscription
from utils import *
import reveal

from django.utils.translation import ugettext as _

class Unsubscribe(Handler):
    def get(self):
        email = self.request.get('email')
        token = self.request.get('token')
        is_verified = reveal.verify('unsubscribe:%s' % email, token)
        if not is_verified:
            return self.error(200, _('This link is invalid.'))

        subscription = Subscription.get(self.repo, self.params.id, email)
        if subscription:
            db.delete(subscription)
            return self.info(200, _('You have successfully unsubscribed.'))
        else:
            return self.error(200, _('You are already unsubscribed.'))

if __name__ == '__main__':
    run(('/unsubscribe', Unsubscribe))
