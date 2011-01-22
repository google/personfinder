#!/usr/bin/python2.5
# Copyright 2011 Google Inc.
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

import logging

from utils import Handler, get_utcnow, set_utcnow_for_test, run
from datetime import datetime

class SetUtcnow(Handler):
  """Set util utcnow based on params, FOR TESTING ONLY."""
  subdomain_required = False # Run at the root domain, not a subdomain.

  def get(self):
      # look for the 'utcnow' param and set current time for test based on it.
      utcnow = self.params.utcnow
      if self.is_test_mode():
          try:
              logging.info('Setting utcnow to "%s"' % utcnow)
              set_utcnow_for_test(utcnow)
              self.render('templates/set_utcnow.html', utcnow=get_utcnow())
          except Exception, e:
              # bad param.
              return self.error(400, 'bad timestamp %s, e=%s' % (utcnow, e))
      else: 
          return self.error(404, 'page not found')


if __name__ == '__main__':
    run(('/admin/set_utcnow_for_test', SetUtcnow))
