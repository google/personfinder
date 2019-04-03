import os
import unittest

import django
import django.test
from google.appengine.ext import testbed

import model

import django_tests_base


class AdminStatisticsViewTests(django_tests_base.DjangoTestsBase):

    def setUp(self):
        super(AdminStatisticsViewTests, self).setUp()
        model.Repo(key_name='haiti').put()
        self.counter = model.UsageCounter.create('haiti')
        self.login(is_admin=True)

    def test_person_counter(self):
        setattr(self.counter, 'person', 3)
        self.counter.put()
        doc = self.to_doc(self.client.get('/global/admin/statistics/'))
        assert 'haiti' in doc.text
        assert '# Persons' in doc.text
        assert doc.cssselect_one('#haiti-persons').text == '3'

    def test_note_counter(self):
        setattr(self.counter, 'note', 5)
        setattr(self.counter, 'unspecified', 5)
        self.counter.put()
        doc = self.to_doc(self.client.get('/global/admin/statistics/'))
        assert 'haiti' in doc.text
        assert '# Note' in doc.text
        assert doc.cssselect_one('#haiti-notes').text == '5'
        assert doc.cssselect_one('#haiti-num_notes_unspecified').text == '5'

    def test_is_note_author_counter(self):
        setattr(self.counter, 'note', 1)
        setattr(self.counter, 'is_note_author', 1)
        self.counter.put()
        doc = self.to_doc(self.client.get('/global/admin/statistics/'))
        assert doc.cssselect_one('#haiti-num_notes_is_note_author').text == '1'

    def test_status_counter(self):

        def set_counter_and_check(status_name, num):
            setattr(self.counter, status_name, num)
            self.counter.put()
            doc = self.to_doc(self.client.get('/global/admin/statistics/'))
            assert 'haiti' in doc.text
            assert status_name in doc.text
            assert doc.cssselect_one(
                '#haiti-num_notes_%s' % status_name).text == str(num)

        set_counter_and_check('is_note_author', 3)
        set_counter_and_check('believed_alive', 5)
        set_counter_and_check('believed_dead', 2)
        set_counter_and_check('believed_missing', 4)
        set_counter_and_check('information_sought', 6)
