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

import config
import const
import model
import modelmodule.admin_acls as admin_acls_model


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
        'author_phone': '111-111-1111',
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

    _DEFAULT_AUTHORIZATION_PARAMS = {
        'contact_name': 'Bob Vance',
        'contact_email': 'bob@fridge.com',
        'organization_name': 'Vance Refrigeration',
        'domain_write_permission': 'fridge.com',
        'read_permission': True,
        'full_read_permission': True,
        'search_permission': True,
        'subscribe_permission': False,
        'mark_notes_reviewed': False,
        'believed_dead_permission': False,
        'stats_permission': False,
        'is_valid': True,
    }

    # 2019-05-12 15:50:01 UTC
    DEFAULT_REPO_UPDATED_DATE = 1557676201

    def repo(
            self, store=True, repo_id='haiti',
            activation_status=model.Repo.ActivationStatus.ACTIVE):
        repo = model.Repo(key_name=repo_id, activation_status=activation_status)
        if store:
            repo.put()
        return repo

    def setup_repo_config(
            self,
            repo_id='haiti',
            updated_date=DEFAULT_REPO_UPDATED_DATE,
            language_menu_options=['en', 'es'],
            repo_titles={'en': 'Haiti', 'es': 'Haití'},
            map_default_center=[123.45, 67.89],
            map_default_zoom=8):
        config.set_for_repo(
            repo_id,
            updated_date=updated_date,
            language_menu_options=language_menu_options,
            repo_titles=repo_titles,
            map_default_center=map_default_center,
            map_default_zoom=map_default_zoom)

    def person(
            self, store=True, index=False, repo_id='haiti', record_id=None,
            **kwargs):
        if not record_id:
            record_id = '%s.%s/Person.%d' % (
                repo_id, const.HOME_DOMAIN, model.UniqueId.create_id())
        key_name = '%s:%s' % (repo_id, record_id)
        params = copy.deepcopy(TestDataGenerator._DEFAULT_PERSON_A_PARAMS)
        params.update(kwargs)
        person = model.Person(key_name=key_name, repo=repo_id, **params)
        if index:
            person.update_index(['old', 'new'])
        if store:
            person.put()
        return person

    def person_a(self, store=True, index=False, repo_id='haiti', **kwargs):
        return self.person(store=store, index=index, repo_id=repo_id, **kwargs)

    def person_b(self, store=True, index=False, repo_id='haiti', **kwargs):
        params = copy.deepcopy(TestDataGenerator._DEFAULT_PERSON_B_PARAMS)
        params.update(kwargs)
        return self.person(store=store, index=index, repo_id=repo_id, **params)

    def note(
            self, store=True, repo_id='haiti', person_id=None, record_id=None,
            **kwargs):
        if not record_id:
            record_id = '%s.%s/Note.%d' % (
                repo_id, const.HOME_DOMAIN, model.UniqueId.create_id())
        key_name = '%s:%s' % (repo_id, record_id)
        params = copy.deepcopy(TestDataGenerator._DEFAULT_NOTE_PARAMS)
        params.update(kwargs)
        note = model.Note(
            key_name=key_name, repo=repo_id, person_record_id=person_id,
            **params)
        if store:
            note.put()
        return note

    def authorization(
            self, store=True, repo_id='haiti', key='secret_key', **kwargs):
        params = copy.deepcopy(TestDataGenerator._DEFAULT_AUTHORIZATION_PARAMS)
        params.update(kwargs)
        authorization = model.Authorization.create(repo_id, key, **params)
        if store:
            authorization.put()
        return authorization

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

    def admin_permission(
            self, store=True, repo_id='haiti', email_address='l@mib.gov',
            access_level=admin_acls_model.AdminPermission.AccessLevel.MODERATOR,
            expiration_date=datetime.datetime(2011, 1, 20)):
        admin_permission = admin_acls_model.AdminPermission.create(
            repo_id, email_address, access_level, expiration_date)
        if store:
            admin_permission.put()
        return admin_permission
