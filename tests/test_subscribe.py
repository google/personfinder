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

"""Tests for subscribe.py."""

import unittest
import subscribe

class SubscribeTests(unittest.TestCase):
    '''Test Subscribe.'''

    def test_is_email_valid(self):
        # These email addresses are correct
        email = 'test@example.com'
        assert subscribe.is_email_valid(email) == True
        email = 'test2@example.com'
        assert subscribe.is_email_valid(email) == True
        email = 'test3.test@example.com'
        assert subscribe.is_email_valid(email) == True
        email = 'test4.test$test@example.com'
        assert subscribe.is_email_valid(email) == True
        email = 'test6.test$test%test@example.com'
        assert subscribe.is_email_valid(email) == True

        # These email addresses are incorrect
        email = 'test@example'
        assert subscribe.is_email_valid(email) == False
        email = 'test.com'
        assert subscribe.is_email_valid(email) == False

        # Empty string instead of email address
        email = ''
        assert subscribe.is_email_valid(email) == None

if __name__ == '__main__':
    unittest.main()
