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

"""Tests for create.py."""

__author__ = 'kpy@google.com (Ka-Ping Yee)'

import datetime
import unittest

from google.appengine.ext import webapp
from nose.tools import assert_raises

import create


class CreateTests(unittest.TestCase):
    def test_validate_date(self):
        assert create.validate_date('2008-09-12') == \
            datetime.datetime(2008, 9, 12)
        assert_raises(ValueError, create.validate_date, '2008-09-12-1')
        assert_raises(ValueError, create.validate_date, '2008-09')
        assert_raises(ValueError, create.validate_date, '2008-13-12')
        assert_raises(ValueError, create.validate_date, '2008-09-31')
        assert_raises(Exception, create.validate_date, None)


if __name__ == '__main__':
    unittest.main()
