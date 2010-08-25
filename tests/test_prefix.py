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

"""Unittest for prefix.py module."""

from google.appengine.ext import db
import prefix
import unittest


class TestPerson(db.Model):
    name = db.StringProperty()


class PrefixTests(unittest.TestCase):
    def test_normalize(self):
        assert prefix.normalize(u'hi there') == u'HI THERE'
        assert prefix.normalize(u'salut l\xe0') == u'SALUT LA'
        assert prefix.normalize(
            u'L\xf2ng Str\xefng w\xedth l\xf4ts \xf6f \xc3cc\xebnts') == \
            u'LONG STRING WITH LOTS OF ACCENTS'

    def test_add_prefix_properties(self):
        prefix_properties = ['name']
        prefix_types = ['_n_', '_n1_', '_n2_']
        all_properties = ['name', 'name_n1_', 'name_n2_', 'name_n_']
        prefix.add_prefix_properties(TestPerson, 'name')
        # Test the list of prefix properties was recorded
        assert TestPerson._prefix_properties == prefix_properties
        # Test all prefix properties have been added
        for prefix_type in prefix_types:
            assert hasattr(TestPerson, 'name' + prefix_type)
        # Test that the model class was updated
        assert sorted(TestPerson.properties()) == all_properties

    def test_update_prefix_properties(self):
        prefix.add_prefix_properties(TestPerson, 'name')
        test_person = TestPerson(name='John')
        prefix.update_prefix_properties(test_person)
        assert test_person.name_n_ == 'JOHN'
        assert test_person.name_n1_ == 'J'
        assert test_person.name_n2_ == 'JO'

    def test_filter_prefix(self):
        # Test 1-char prefix filter
        test_query = TestPerson.all()
        test_criteria = {'name': 'b'}
        prefix.filter_prefix(test_query, **test_criteria)
        assert test_query._get_query() == {'name_n1_ =': u'B'}
        # Test 2-char prefix filter
        test_query = TestPerson.all()
        test_criteria = {'name': 'bryan'}
        prefix.filter_prefix(test_query, **test_criteria)
        assert test_query._get_query() == {'name_n2_ =': u'BR'}

    def test_get_prefix_matches(self):
        db.put(TestPerson(name='Bryan'))
        db.put(TestPerson(name='Bruce'))
        db.put(TestPerson(name='Benny'))
        db.put(TestPerson(name='Lenny'))
        test_query = TestPerson.all().order('name')
        # Test full string match
        test_criteria = {'name': 'bryan'}
        test_people = list(person.name for person in prefix.get_prefix_matches(
            test_query, 100, **test_criteria))
        assert test_people == ['Bryan']
        # Test 2-char prefix match
        test_criteria = {'name': 'br'}
        test_people = set(person.name for person in prefix.get_prefix_matches(
            test_query, 100, **test_criteria))
        assert test_people == set(['Bruce', 'Bryan'])
        # Test 1-char prefix match
        test_criteria = {'name': 'b'}
        test_people = set(person.name for person in prefix.get_prefix_matches(
            test_query, 100, **test_criteria))
        assert test_people == set(['Benny', 'Bruce', 'Bryan'])
        # Test limit
        test_criteria = {'name': 'b'}
        test_people = set(person.name for person in prefix.get_prefix_matches(
            test_query, 1, **test_criteria))
        assert test_people == set(['Benny'])

if __name__ == '__main__':
    unittest.main()
