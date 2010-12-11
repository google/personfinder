#!/usr/bin/python2.5
#
# Copyright 2010 Google Inc. All Rights Reserved.

"""Unittest for indexing.py module."""

__author__ = 'pfritzsche@google.com (Phil Fritzsch)'

import datetime
import webob
import unittest

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp

import model
import tasks


class TasksTests(unittest.TestCase):
    def tearDown(self):
        db.delete(model.PersonTombstone.all())

    def simulate_request(self, path):
        request = webapp.Request(webob.Request.blank(path).environ)
        response = webapp.Response()
        handler = tasks.ClearTombstones()
        handler.initialize(request, response)
        return handler

    def test_clear_tombstones(self):
        """Tests the clear tombstones cron job."""
        pt_new = model.PersonTombstone(
            subdomain='haiti', record_id='example.org/person.123')
        pt_old = model.PersonTombstone(
            subdomain='haiti', record_id='example.org/person.456')
        pt_old.timestamp -= datetime.timedelta(days=4)
        db.put([pt_new, pt_old])

        handler = self.simulate_request('/tasks/clear_tombstones')
        handler.get()

        assert db.get(pt_new.key())
        assert not db.get(pt_old.key())
