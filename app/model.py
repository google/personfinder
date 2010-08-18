#!/usr/bin/python2.5
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

"""The Person Finder data model, based on PFIF (http://zesty.ca/pfif)."""

__author__  = 'kpy@google.com (Ka-Ping Yee) and many other Googlers'

import datetime

from google.appengine.api import memcache
from google.appengine.ext import db
import config
import indexing
import pfif
import prefix

# The domain of this repository.  Records created on this site ("original
# records") will have record_ids beginning with this domain and a slash.
HOME_DOMAIN = config.HOME_DOMAIN


# ==== PFIF record IDs =====================================================
# In App Engine, entity keys can have numeric ids or string names.  We use
# numeric ids for original records (so we can autogenerate unique ids), and
# string names for clone records (so we can handle external identifiers).
# Here are a few examples, assuming that HOME_DOMAIN is 'example.com':
#   - For an original record (created at this repository):
#         person_record_id: 'example.com/person.123'
#         entity key: db.Key.from_path('Person', 123)
#   - For a clone record (imported from an external repository):
#         person_record_id: 'other.domain.com/3bx7sQz'
#         entity key: db.Key.from_path('Person', 'other.domain.com/3bx7sQz')

def is_original(record_id):
  """Returns True if this is a record_id for an original record."""
  try:
    domain, local_id = record_id.split('/', 1)
    return domain == HOME_DOMAIN
  except ValueError:
    raise ValueError('%r is not a valid record_id' % record_id)

def key_from_record_id(record_id, expected_kind):
  """Returns the datastore Key corresponding to a PFIF record_id."""
  try:
    domain, local_id = record_id.split('/', 1)
    if domain == HOME_DOMAIN:  # original record
      type, id = local_id.split('.')
      kind, id = type.capitalize(), int(id)
      assert kind == expected_kind, 'not a %s: %r' % (expected_kind, record_id)
      return db.Key.from_path(kind, int(id))
    else:  # clone record
      return db.Key.from_path(expected_kind, record_id)
  except ValueError:
    raise ValueError('%r is not a valid record_id' % record_id)

def record_id_from_key(key):
  """Returns the PFIF record_id corresponding to a datastore Key."""
  assert len(key.to_path()) == 2  # We store everything in top-level entities.
  if key.id():  # original record
    return '%s/%s.%d' % (HOME_DOMAIN, str(key.kind().lower()), key.id())
  else:  # clone record
    return key.name()


# ==== Model classes =======================================================

class Base:
  """Mix-in class for methods common to both Person and Note entities."""
  def is_original(self):
    """Returns True if this record was created in this repository."""
    return self.key().id() is not None

  def is_clone(self):
    """Returns True if this record was imported from another repository."""
    return not self.is_original()

  def get_domain(self):
    """Returns the domain name of this record's original repository."""
    return record_id_from_key(self.key()).split('/')[0]


# All fields are either required, or have a default value.  For property
# types with a false value, the default is the false value.  For types with
# no false value, the default is None.

class Person(db.Model, Base):
  """The datastore entity kind for storing a PFIF Person record."""

  # The entry_date should update every time a record is created or re-imported.
  entry_date = db.DateTimeProperty(required=True)

  author_name = db.StringProperty(default='', multiline=True)
  author_email = db.StringProperty(default='')
  author_phone = db.StringProperty(default='')
  source_name = db.StringProperty(default='')
  source_date = db.DateTimeProperty()
  source_url = db.StringProperty(default='')

  first_name = db.StringProperty(required=True)
  last_name = db.StringProperty()
  sex = db.StringProperty(default='', choices=pfif.PERSON_SEX_VALUES)
  date_of_birth = db.StringProperty(default='')  # YYYY, YYYY-MM, or YYYY-MM-DD
  age = db.StringProperty(default='')  # NN or NN-MM
  home_street = db.StringProperty(default='')
  home_neighborhood = db.StringProperty(default='')
  home_city = db.StringProperty(default='')
  home_state = db.StringProperty(default='')
  home_postal_code = db.StringProperty(default='')
  home_country = db.StringProperty(default='')
  photo_url = db.StringProperty(default='')
  other = db.TextProperty(default='')

  # found==true iff there is a note with found==true
  found = db.BooleanProperty(default=False)

  # Time of the last creation/update of this Person or a Note on this Person.
  # This reflects any change to the Person page.
  last_update_date = db.DateTimeProperty()

  # attributes used by indexing.py
  names_prefixes = db.StringListProperty()
  _fields_to_index_properties = ['first_name', 'last_name']
  _fields_to_index_by_prefix_properties = ['first_name', 'last_name']

  @property
  def person_record_id(self):
    """Returns the fully qualified PFIF identifier for this record."""
    return record_id_from_key(self.key())

  def get_linked_persons(self, note_limit=200):
    """Retrieves the Persons linked to this Person.

    Linked persons represent duplicate Person entries.
    """
    linked_persons = []
    for note in Note.get_by_person_record_id(
        self.person_record_id, limit=note_limit):
      try:
        person = Person.get_by_person_record_id(note.linked_person_record_id)
      except:
        continue
      if person:
        linked_persons.append(person)
    return linked_persons

  @classmethod
  def get_by_person_record_id(cls, person_record_id):
    """Retrieves a Person by its fully qualified unique identifier."""
    return Person.get(key_from_record_id(person_record_id, 'Person'))

  def update_index(self, which_indexing):
    #setup new indexing
    if 'new' in which_indexing:
      indexing.update_index_properties(self)
    # setup old indexing
    if 'old' in which_indexing:
      prefix.update_prefix_properties(self)

#old indexing
prefix.add_prefix_properties(
    Person, 'first_name', 'last_name', 'home_street', 'home_neighborhood',
    'home_city', 'home_state', 'home_postal_code')


class Note(db.Model, Base):
  """The datastore entity kind for storing a PFIF note record."""

  # The entry_date should update every time a record is re-imported.
  entry_date = db.DateTimeProperty(auto_now=True)

  person_record_id = db.StringProperty(required=True)

  # Use this field to store the person_record_id of a duplicate Person entry.
  linked_person_record_id = db.StringProperty(default='')

  author_name = db.StringProperty(default='', multiline=True)
  author_email = db.StringProperty(default='')
  author_phone = db.StringProperty(default='')
  source_date = db.DateTimeProperty()

  status = db.StringProperty(default='', choices=pfif.NOTE_STATUS_VALUES)
  found = db.BooleanProperty()
  email_of_found_person = db.StringProperty(default='')
  phone_of_found_person = db.StringProperty(default='')
  last_known_location = db.StringProperty(default='')
  text = db.TextProperty(default='')

  @property
  def note_record_id(self):
    """Returns the fully qualified unique identifier for this record."""
    return record_id_from_key(self.key())

  @classmethod
  def get_by_note_record_id(cls, note_record_id):
    """Retrieves a Note by its fully qualified PFIF identifier."""
    return Note.get(key_from_record_id(note_record_id, 'Note'))

  @classmethod
  def get_by_person_record_id(cls, person_record_id, limit=200):
    """Retreive notes for a person record, ordered by entry_date."""
    query = Note.all().filter('person_record_id =', person_record_id)
    return query.order('entry_date').fetch(limit)


class Photo(db.Model):
  """An entity kind for storing uploaded photos."""
  bin_data = db.BlobProperty()
  date = db.DateTimeProperty(auto_now_add=True)


class Authorization(db.Model):
  """Authorization tokens for the write API."""
  auth_key = db.StringProperty(required=True)
  domain = db.StringProperty(required=True)

  # Bookkeeping information for humans, not used programmatically.
  contact_name = db.StringProperty()
  contact_email = db.StringProperty()
  organization_name = db.StringProperty()


class Secret(db.Model):
  """A place to store application-level secrets in the database."""
  secret = db.BlobProperty()


class EntityCounter(db.Model):
  """Stores a count of the entities of a particular kind."""
  timestamp = db.DateTimeProperty(auto_now=True)
  kind_name = db.StringProperty(required=True)

  last_key = db.StringProperty(default='')  # if non-null, count is partial
  count = db.IntegerProperty(default=0)

  @classmethod
  def query_last(cls, kind):
    return cls.all().filter('kind_name =', kind.__name__).order('-timestamp')

  @classmethod
  def get_count(cls, kind):
    cache_key = 'count.' + kind.__name__
    count = memcache.get(cache_key)
    if not count:
      # The __key__ index is unreliable and sometimes yields an incorrectly
      # low count.  Work around this by using the max of the last few counts.
      counters = cls.query_last(kind).filter('last_key =', '').fetch(10)
      count = max([counter.count for counter in counters] + [0])
      # Cache the count for one minute.  During this time after an update,
      # users may see either the old or the new count.
      memcache.set(cache_key, count, 60)
    return count

class StaticSiteMapInfo(db.Model):
  """Holds static sitemaps file info"""
  static_sitemaps = db.StringListProperty()
  static_sitemaps_generation_time = db.DateTimeProperty(required=True)
  shard_size_seconds = db.IntegerProperty(default=90)
  
class SiteMapPingStatus(db.Model):
  """Tracks the last shard index that was pinged to the search engine"""
  search_engine = db.StringProperty(required=True)
  shard_index = db.IntegerProperty(default=-1)
