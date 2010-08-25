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

__author__ = 'kpy@google.com (Ka-Ping Yee) and many other Googlers'

import datetime

from google.appengine.api import memcache
from google.appengine.ext import db
import indexing
import pfif
import prefix

# The domain name of this application.  The application hosts multiple
# repositories, each at a subdomain of this domain.
HOME_DOMAIN = 'person-finder.appspot.com'


# ==== PFIF record IDs =====================================================
# All Person and Note entities have record IDs as their string key names.

def is_original(record_id):
    """Returns True if this is a record_id for an original record
    (a record originally created in this repository)."""
    try:
        domain, local_id = record_id.split('/', 1)
        if domain == HOME_DOMAIN:  # not allowed, must be a subdomain
            raise ValueError
        if '.' in domain:
            subdomain, domain = domain.split('.', 1)
            return domain == HOME_DOMAIN
    except ValueError:
        raise ValueError('%r is not a valid record_id' % record_id)

def is_clone(record_id):
    """Returns True if this is a record_id for a clone record (a record
    created in another repository and copied into this one)."""
    return not is_original(record_id)

def filter_by_prefix(query, key_name_prefix):
    """Filters a query for key_names that have the given prefix.  If root_kind
    is specified, filters the query for children of any entities that are of
    that kind with the given prefix; otherwise, the results are assumed to be
    top-level entities of the kind being queried."""
    root_kind = query._model_class.__name__
    min_key = db.Key.from_path(root_kind, key_name_prefix)
    max_key = db.Key.from_path(root_kind, key_name_prefix + u'\uffff')
    return query.filter('__key__ >=', min_key).filter('__key__ <=', max_key)


# ==== Model classes =======================================================

class Subdomain:
    """A separate grouping of Person and Note records.  This is a top-level
    entity, with no parent, whose existence just indicates the existence of
    a subdomain.  Key name: unique subdomain name.  In the UI, each subdomain
    appears to be an independent instance of the application."""
    pass  # No properties for now; only the key_name is significant.


class Base(db.Model):
    """Base class providing methods common to both Person and Note entities."""

    def is_original(self):
        """Returns True if this record was created in this repository."""
        return is_original(self.key().name())

    def is_clone(self):
        """Returns True if this record was imported from another repository."""
        return not self.is_original()

    def get_domain(self):
        """Returns the domain name of this record's original repository."""
        return self.key().name().split('/')[0]

    def get_subdomain(self):
        """Returns the subdomain of an original record."""
        assert self.is_original()
        return self.get_domain().split('.')[0]

    def all_in_subdomain(cls, subdomain):
        """Gets a query for all entities with the given subdomain."""
        return filter_by_prefix(cls.all(), subdomain + '.' + HOME_DOMAIN + '/')

    @classmethod
    def create_original(cls, subdomain, **kwargs):
        """Creates a new original Person entity with the given field values."""
        key_name = '%s.%s/%s.%d' % (
            subdomain, HOME_DOMAIN, cls.__name__.lower(), UniqueId.create_id())
        return cls(key_name=key_name, **kwargs)

    @classmethod
    def create_clone(cls, record_id, **kwargs):
        """Creates a new clone Person entity with the given field values."""
        assert is_clone(record_id)
        return cls(key_name=record_id, **kwargs)


# All fields are either required, or have a default value.  For property
# types with a false value, the default is the false value.  For types with
# no false value, the default is None.

class Person(Base):
    """The datastore entity kind for storing a PFIF person record.  Never call
    Person() directly; use Person.create_clone() or Person.create_original()."""

    # entry_date should update every time a record is created or re-imported.
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
    date_of_birth = db.StringProperty(default='')  # YYYY, YYYY-MM, YYYY-MM-DD
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
        return self.key().name()

    def get_linked_persons(self, note_limit=200):
        """Retrieves the Persons linked to this Person.

        Linked persons represent duplicate Person entries.
        """
        linked_persons = []
        for note in Note.get_by_person_record_id(
                self.person_record_id, limit=note_limit):
            try:
                person = Person.get_by_person_record_id(
                    note.linked_person_record_id)
            except:
                continue
            if person:
                linked_persons.append(person)
        return linked_persons

    @classmethod
    def get_by_person_record_id(cls, person_record_id):
        """Retrieves a Person by its fully qualified unique identifier."""
        return Person.get_by_key_name(person_record_id)

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


class Note(Base):
    """The datastore entity kind for storing a PFIF note record.  Never call
    Note() directly; use Note.create_clone() or Note.create_original()."""

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
        return self.key().name()

    @classmethod
    def get_by_note_record_id(cls, note_record_id):
        """Retrieves a Note by its fully qualified PFIF identifier."""
        return Note.get_by_key_name(note_record_id)

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
        return cls.all().filter(
            'kind_name =', kind.__name__).order('-timestamp')

    @classmethod
    def get_count(cls, kind):
        cache_key = 'count.' + kind.__name__
        count = memcache.get(cache_key)
        if not count:
            # The __key__ index is unreliable and sometimes yields an
            # incorrectly low count.  Work around this by using the
            # maximum of the last few counts.
            counters = cls.query_last(kind).filter('last_key =', '').fetch(10)
            count = max([counter.count for counter in counters] + [0])
            # Cache the count for one minute.  During this time after an
            # update, users may see either the old or the new count.
            memcache.set(cache_key, count, 60)
        return count

class StaticSiteMapInfo(db.Model):
    """Holds static sitemaps file info."""
    static_sitemaps = db.StringListProperty()
    static_sitemaps_generation_time = db.DateTimeProperty(required=True)
    shard_size_seconds = db.IntegerProperty(default=90)
    
class SiteMapPingStatus(db.Model):
    """Tracks the last shard index that was pinged to the search engine."""
    search_engine = db.StringProperty(required=True)
    shard_index = db.IntegerProperty(default=-1)


class UniqueId(db.Model):
    """This entity is used just to generate unique numeric IDs."""
    @staticmethod
    def create_id():
        """Gets an integer ID that is guaranteed to be different from any ID
        previously returned by this static method."""
        unique_id = UniqueId()
        unique_id.put()
        return unique_id.key().id()
