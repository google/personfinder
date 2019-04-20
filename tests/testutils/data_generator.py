# encoding: utf-8
# Copyright 2019 Google Inc.
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
"""Utilities for generating test data."""

import copy
import datetime

import six

import model


class TestDataGenerator(object):
    """Tool for generating (and, optionally, storing) test entities."""

    _DEFAULT_PERSON_A_PARAMS = {
        'given_name': 'John',
        'family_name': 'Smith',
        'home_city': 'Toronto',
        'home_state': 'Ontario',
        'home_postal_code': 'M4V 2C5',
        'home_neighborhood': 'Deer Park',
        'author_name': 'Alice Smith',
        'author_photo': '111-111-1111',
        'author_email': 'alice.smith@example.com',
        'source_name': 'Example Organization',
        'source_url': 'http://www.example.org/person123',
        'source_date': datetime.datetime(2010, 1, 1),
        'entry_date': datetime.datetime(2010, 1, 1),
        'expiry_date': datetime.datetime(2010, 2, 1),
    }

    _DEFAULT_PERSON_B_PARAMS = {
        'given_name': 'Luis',
        'family_name': six.u('Fernández'),
        'home_city': 'Mexico City',
        'home_state': 'Federal District',
        'source_date': datetime.datetime(2010, 1, 1),
        'entry_date': datetime.datetime(2010, 1, 1),
        'expiry_date': datetime.datetime(2010, 3, 1),
    }

    _DEFAULT_NOTE_PARAMS = {
        'status': 'believed_missing',
        'author_made_contact': False,
        'entry_date': datetime.datetime(2010, 1, 1),
        'source_date': datetime.datetime(2010, 1, 2),
    }

    def repo(self, store=True, repo_id='haiti'):
        repo = model.Repo(key_name=repo_id)
        if store:
            repo.put()
        return repo

    def person(self, store=True, repo_id='haiti', **kwargs):
        params = copy.deepcopy(TestDataGenerator._DEFAULT_PERSON_A_PARAMS)
        params.update(kwargs)
        person = model.Person.create_original(repo_id, **params)
        if store:
            person.put()
        return person

    def person_a(self, **kwargs):
        return self.person(**kwargs)

    def person_b(self, store=True, repo_id='haiti', **kwargs):
        params = copy.deepcopy(TestDataGenerator._DEFAULT_PERSON_B_PARAMS)
        params.update(kwargs)
        person = model.Person.create_original(repo_id, **params)
        if store:
            person.put()
        return person

    def note(self, store=True, repo_id='haiti', person_id=None, **kwargs):
        params = copy.deepcopy(TestDataGenerator._DEFAULT_NOTE_PARAMS)
        params.update(kwargs)
        note = model.Note.create_original(
            repo_id, person_record_id=person_id, **params)
        if store:
            note.put()
        return note

    def photo(self, store=True, repo_id='haiti', image_data='xyz'):
        photo = model.Photo.create(repo_id, image_data=image_data)
        if store:
            photo.put()
        return photo

    def subscription(
        self, store=True, repo_id='haiti', person_id=None,
        email='fred@example.net', language='en',
        timestamp=datetime.datetime(2010, 1, 2)):
        subscription = model.Subscription(
            repo=repo_id,
            person_record_id=person_id,
            email=email,
            language=language,
            timestamp=timestamp)
        if store:
            subscription.put()
        return subscription
