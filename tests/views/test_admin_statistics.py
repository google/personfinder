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

import model

import view_tests_base


class AdminStatisticsViewTests(view_tests_base.ViewTestsBase):

    def setUp(self):
        super(AdminStatisticsViewTests, self).setUp()
        self.data_generator.repo()
        self.counter = model.UsageCounter.create('haiti')
        self.login_as_manager()

    def get_page_doc(self):
        return self.to_doc(self.client.get('/global/admin/statistics/',
                                           secure=True))

    def test_person_counter(self):
        self.counter.person = 3
        self.counter.put()
        doc = self.get_page_doc()
        assert 'haiti' in doc.text
        assert '# Persons' in doc.text
        assert doc.cssselect_one('#haiti-persons').text == '3'

    def test_note_counter(self):
        self.counter.note = 5
        self.counter.unspecified = 5
        self.counter.put()
        doc = self.get_page_doc()
        assert 'haiti' in doc.text
        assert '# Note' in doc.text
        assert doc.cssselect_one('#haiti-notes').text == '5'
        assert doc.cssselect_one('#haiti-num_notes_unspecified').text == '5'

    def test_is_note_author_counter(self):
        self.counter.note = 1
        self.counter.is_note_author = 1
        self.counter.put()
        doc = self.get_page_doc()
        assert doc.cssselect_one('#haiti-num_notes_is_note_author').text == '1'

    def test_status_counter(self):

        def set_counter_and_check(status_name, num):
            setattr(self.counter, status_name, num)
            self.counter.put()
            doc = self.get_page_doc()
            assert 'haiti' in doc.text
            assert status_name in doc.text
            assert doc.cssselect_one(
                '#haiti-num_notes_%s' % status_name).text == str(num)

        set_counter_and_check('is_note_author', 3)
        set_counter_and_check('believed_alive', 5)
        set_counter_and_check('believed_dead', 2)
        set_counter_and_check('believed_missing', 4)
        set_counter_and_check('information_sought', 6)
