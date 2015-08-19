#!/usr/bin/python2.7
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

"""Unittest for api.py module."""

__author__ = 'ichikawa@google.com (Hiroshi Ichikawa)'

import datetime
import logging
import sys
import unittest

import api
import model
import test_handler

class APITests(unittest.TestCase):

    def test_sms_render_person(self):
        handler = test_handler.initialize_handler(
            api.HandleSMS, 'api/handle_sms')

        person = model.Person.create_original(
            'haiti',
            full_name='John Smith',
            latest_status='believed_alive',
            sex='male',
            age='30',
            home_city='Los Angeles',
            home_state='California',
            entry_date=datetime.datetime(2010, 1, 1))
        assert (handler.render_person(person) ==
            'John Smith / '
            'Someone has received information that this person is alive / '
            'male / 30 / From: Los Angeles California')

        person = model.Person.create_original(
            'haiti',
            full_name='John Smith',
            entry_date=datetime.datetime(2010, 1, 1))
        assert handler.render_person(person) == 'John Smith'

        person = model.Person.create_original(
            'haiti',
            full_name='John Smith',
            home_state='California',
            entry_date=datetime.datetime(2010, 1, 1))
        assert handler.render_person(person) == 'John Smith / From: California'
