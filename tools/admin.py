# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions for administration in the interactive console."""

from model import *
from utils import *
import logging


class Mapper(object):
    # Subclasses should replace this with a model class (eg, model.Person).
    KIND = None

    # Subclasses can replace this with a list of (property, value) tuples
    # to filter by.
    FILTERS = []

    def map(self, entity):
        """Updates a single entity.

        Implementers should return a tuple containing two iterables
        (to_update, to_delete)."""
        return ([], [])


    def get_query(self):
        """Returns a query over the specified kind, with any appropriate
        filters applied."""
        q = self.KIND.all()
        for prop, value in self.FILTERS:
            q.filter("%s =" % prop, value)
        q.order("__key__")
        return q

    def run(self, batch_size=100):
        """Executes the map procedure over all matching entities."""
        q = self.get_query()
        entities = q.fetch(batch_size)
        while entities:
            to_put = []
            to_delete = []
            for entity in entities:
                map_updates, map_deletes = self.map(entity)
                to_put.extend(map_updates)
                to_delete.extend(map_deletes)
            if to_put:
                db.put(to_put)
                logging.info('entities written: %d' % len(to_put))
            if to_delete:
                db.delete(to_delete)
                logging.info('entities deleted: %d' % len(to_delete))
            q = self.get_query()
            q.filter("__key__ >", entities[-1].key())
            entities = q.fetch(batch_size)


class Reindexer(Mapper):
    KIND = Person
    def map(self, entity):
        # This updates both old and new index and we need it for now,
        # as first stage of deployment.
        entity.update_index(['old','new'])
        # Use the next line to index only with new index
        #indexing.update_index_properties(entity)
        return [entity], []

def Person_repr(person):
    return '<Person %s %r %r>' % (
          person.person_record_id, person.first_name, person.last_name)

def Note_repr(note):
    return '<Note %s for %s by %r at %s>' % (
          note.note_record_id, note.person_record_id,
          note.author_name, note.entry_date)

Person.__repr__ = Person_repr
Note.__repr__ = Note_repr

def expand_id(id):
    id = str(id)
    if '/' not in id:
        id = HOME_DOMAIN + '/person.' + id
    return id

def clear_found(id):
    person = get_person(id)
    person.found = False
    db.put(person)

def get_person(id):
    return Person.get_by_person_record_id(expand_id(id))

def get_notes(id):
    return list(Note.all().filter('person_record_id =', expand_id(id)))

def delete_person(id):
    entities = get_entities_for_person(id)
    db.delete(entities)

def get_entities_for_person(id):
    person = get_person(id)
    notes = get_notes(id)
    entities = [person] + notes
    if person.photo_url:
        if person.photo_url.startswith('/photo?id='):
            id = person.photo_url.split('=', 1)[1]
            photo = db.get(id)
            if photo.kind() == 'Photo':
                entities.append(photo)
    return entities
