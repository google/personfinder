# Copyright 2011 Google Inc.
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
import pickle


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
          person.record_id, person.given_name, person.family_name)

def Note_repr(note):
    return '<Note %s for %s by %r at %s>' % (
          note.record_id, note.person_record_id,
          note.author_name, note.entry_date)

Person.__repr__ = Person_repr
Note.__repr__ = Note_repr

def expand_id(repo, id):
    id = str(id)
    if '/' not in id:
        id = repo + '.' + HOME_DOMAIN + '/person.' + id
    return id

def clear_found(id):
    person = get_person(id)
    person.found = False
    db.put(person)

def get_person(repo, id):
    return Person.get(repo, expand_id(repo, id))

def get_notes(repo, id):
    return list(Note.all_in_repo(repo).filter(
        'person_record_id =', expand_id(repo, id)))

def delete_person(person):
    """Deletes a Person, possibly leaving behind an empty placeholder."""
    if person.is_original():
        person.expiry_date = get_utcnow()
        person.put_expiry_flags()
        person.wipe_contents()
    else:
        person.delete_related_entities(delete_self=True)

def delete_repo(repo):
    """Deletes a Repo and associated Person, Note, Authorization, Subscription
    (but not Counter, ApiActionLog, or UserAgentLog) entities."""
    for person in Person.all_in_repo(repo, filter_expired=False):
        delete_person(person)
    entities = [Repo.get_by_key_name(repo)]
    for cls in [Person, Note, Authorization, Subscription]:
        entities += list(cls.all().filter('repo =', repo))
    min_key = db.Key.from_path('ConfigEntry', repo + ':')
    max_key = db.Key.from_path('ConfigEntry', repo + ';')
    entities += list(config.ConfigEntry.all().filter('__key__ >', min_key
                                            ).filter('__key__ <', max_key))
    db.delete(entities)

def get_all_resources():
    """Gets all the Resource entities and returns a dictionary of the contents.

    The resulting dictionary has the structure: {
      <bundle_name>: {
        'created': <bundle_created_datetime>,
        'resources': {
            <resource_name>: {
                'cache_seconds': <cache_seconds>
                'content': <content_string>
                'last_modified': <last_modified_datetime>
            }
        }
    }
    """
    import resources
    bundle_dicts = {}
    for b in resources.ResourceBundle.all():
        resource_dicts = {}
        for r in resources.Resource.all().ancestor(b):
            resource_dicts[r.key().name()] = {
                'cache_seconds': r.cache_seconds,
                'content': r.content,
                'last_modified': r.last_modified
            }
        bundle_dicts[b.key().name()] = {
            'created': b.created,
            'resources': resource_dicts
        }
    return bundle_dicts

def download_resources(filename):
    """Downloads all the Resource data into a backup file in pickle format."""
    file = open(filename, 'w')
    pickle.dump(get_all_resources(), file)
    file.close()
