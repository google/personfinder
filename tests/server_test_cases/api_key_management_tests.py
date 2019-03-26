#!/usr/bin/python2.7
# encoding: utf-8
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

"""Test cases for end-to-end testing.  Run with the server_tests script."""

import calendar
import datetime
import email
import email.header
import optparse
import os
import pytest
import re
import simplejson
import sys
import tempfile
import time
import unittest
import urlparse

from google.appengine.api import images

import config
from const import ROOT_URL, PERSON_STATUS_TEXT, NOTE_STATUS_TEXT
import download_feed
from model import *
from photo import MAX_IMAGE_DIMENSION
import remote_api
from resources import Resource, ResourceBundle
import reveal
import scrape
import setup_pf as setup
from test_pfif import text_diff
from text_query import TextQuery
import utils
from server_tests_base import ServerTestsBase


# TODO(ryok): fix go_as_operator() and re-enable the tests.
#class ApiKeyManagementTests(ServerTestsBase):
#    """Tests for API key management capabilities."""
#
#    key_management_operator = "op@example.com"
#    
#    def go_as_operator(self, path, **kwargs):
#        """Navigates to the given path with an operator login."""
#        if not self.logged_in_as_operator:
#            scrape.setcookies(self.s.cookiejar, self.hostport,
#                              ['dev_appserver_login=%s:True:1' %
#                                  self.key_management_operator])
#            self.logged_in_as_operator = True
#        return self.go(path, **kwargs)
#
#    def go_as_admin(self, path, **kwargs):
#        """Setting logged_in_as_operator to False."""
#        ret = ServerTestsBase.go_as_admin(self, path, **kwargs)
#        self.logged_in_as_operator = False
#        return ret
#
#    def setUp(self):
#        ServerTestsBase.setUp(self)
#        self.logged_in_as_operator = False
#        config.set_for_repo(
#            'japan',
#            key_management_operators=[self.key_management_operator])
#
#    def test_toppage(self):
#        """Check the main page of API kay management."""
#        url = 'http://%s/personfinder/japan/admin/api_keys' % self.hostport
#        doc = self.go(url, redirects=0)
#        # check if 302
#        assert self.s.status == 302
#        doc = self.go_as_operator(url, redirects=0)
#        assert self.s.status == 200
#        assert 'API Key Management' in doc.text
#        doc = self.go_as_admin(url, redirects=0)
#        assert self.s.status == 200
#        assert 'API Key Management' in doc.text
#
#    def test_manage_key(self):
#        """Check if a new API key is created/updated correctly."""
#        url = 'http://%s/personfinder/japan/admin/api_keys' % self.hostport
#        doc = self.go_as_operator(url)
#        assert self.s.status == 200
#        assert 'API Key Management' in doc.text
#        form = doc.cssselect_one('form#create-or-update-api-key')
#        contact_name = 'Test User'
#        contact_email = 'user@example.com'
#        organization_name = 'Example, Inc.'
#        domain_write_permission = 'example.com'
#        doc = self.s.submit(
#            form,
#            contact_name=contact_name,
#            contact_email=contact_email,
#            organization_name=organization_name,
#            domain_write_permission=domain_write_permission,
#            read_permission='on',
#            full_read_permission='on',
#            search_permission='on',
#            subscribe_permission='on',
#            mark_notes_reviewed='on',
#            is_valid='on',
#        )
#        assert 'A new API key has been created successfully.' in doc.text
#        q = Authorization.all().filter('repo =', 'japan')
#        authorizations = q.fetch(10)
#        assert len(authorizations) == 1
#        authorization = authorizations[0]
#        # Check if the new key is correct.
#        assert authorization.contact_name == contact_name
#        assert authorization.contact_email == contact_email
#        assert authorization.organization_name == organization_name
#        assert authorization.domain_write_permission == domain_write_permission
#        assert authorization.read_permission is True
#        assert authorization.full_read_permission is True
#        assert authorization.search_permission is True
#        assert authorization.subscribe_permission is True
#        assert authorization.mark_notes_reviewed is True
#        assert authorization.is_valid is True
#        # Check if the management self.log is created correctly.
#        q = ApiKeyManagementLog.all().filter('repo =', 'japan')
#        logs = q.fetch(10)
#        assert len(logs) == 1
#        self.log = logs[0]
#        assert self.log.user.email() == self.key_management_operator
#        assert self.log.authorization.key() == authorization.key()
#        assert self.log.action == ApiKeyManagementLog.CREATE
#
#        # List the key and click the edit form on the list
#        url = 'http://%s/personfinder/japan/admin/api_keys/list' % self.hostport
#        doc = self.go_as_admin(url)
#        assert self.s.status == 200
#        assert 'Listing API keys for japan' in doc.text
#        form = doc.cssselect_one('form')
#        doc = self.s.submit(form)
#        assert self.s.status == 200
#        assert 'Detailed information of an API key for japan' in doc.text
#
#        # Update the key
#        contact_name = 'Japanese User'
#        contact_email = 'user@example.jp'
#        organization_name = 'Example, Corp.'
#
#        form = doc.cssselect_one('form')
#        doc = self.s.submit(
#            form,
#            contact_name=contact_name,
#            contact_email=contact_email,
#            organization_name=organization_name,
#            domain_write_permission='',
#            read_permission='',
#            full_read_permission='',
#            search_permission='',
#            subscribe_permission='',
#            mark_notes_reviewed='',
#            is_valid='',
#            key=str(authorization.key()),
#        )
#        assert 'The API key has been updated successfully.' in doc.text
#        q = Authorization.all().filter('repo =', 'japan')
#        authorizations = q.fetch(10)
#        assert len(authorizations) == 1
#        authorization = authorizations[0]
#        # Check if the new key is correct.
#        assert authorization.contact_name == contact_name
#        assert authorization.contact_email == contact_email
#        assert authorization.organization_name == organization_name
#        assert authorization.domain_write_permission == ''
#        assert authorization.read_permission is False
#        assert authorization.full_read_permission is False
#        assert authorization.search_permission is False
#        assert authorization.subscribe_permission is False
#        assert authorization.mark_notes_reviewed is False
#        assert authorization.is_valid is False
#        # Check if the management self.log is created correctly.
#        q = ApiKeyManagementLog.all().filter('repo =', 'japan')
#        logs = q.fetch(10)
#        assert len(logs) == 2
#        for self.log in logs:
#            assert self.log.user.email() == self.key_management_operator
#            assert self.log.authorization.key() == authorization.key()
#            if self.log.action != ApiKeyManagementLog.CREATE:
#                assert self.log.action == ApiKeyManagementLog.UPDATE
