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

from utils import BaseHandler, get_utcnow, set_utcnow_for_test
from datetime import datetime

class Handler(BaseHandler):
  """Sets or clears the utcnow_for_test value, FOR TESTING ONLY.

  To unset utcnow_for_test:
  http://localhost:8080/admin/set_utcnow_for_test?test_mode=yes

  To set utcnow_for_test:
  http://localhost:8080/admin/set_utcnow_for_test?utcnow=1295662977&test_mode=yes

  The timestamp should be in time.time() format.  One way to get this value
  would be to create a datetime object and call time.mktime(dt.utctimetuple()).
  Time objects lack timezone info, so make sure the input value is UTC.
"""
  repo_required = False  # not specific to a repository

  def get(self):
      utcnow_before_change = get_utcnow()
      utcnow = self.params.utcnow
      if self.is_test_mode():
          try:
              logging.info('Setting utcnow to %r' % utcnow)
              set_utcnow_for_test(utcnow)
              self.render('templates/set_utcnow.html', utcnow=get_utcnow(),
                          utcbefore=utcnow_before_change)
          except Exception, e:
              # bad param.
              return self.error(400, 'bad timestamp %s, e=%s' % (utcnow, e))
      else:
          return self.error(404, 'page not found')
