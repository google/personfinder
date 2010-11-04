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

def is_original(subdomain, record_id):
    """Returns True if this is a record_id for an original record in the given
    subdomain (a record originally created in this subdomain's repository)."""
    try:
        domain, local_id = record_id.split('/', 1)
        return domain == subdomain + '.' + HOME_DOMAIN
    except ValueError:
        raise ValueError('%r is not a valid record_id' % record_id)

def is_clone(subdomain, record_id):
    """Returns True if this is a record_id for a clone record (a record created
    in another repository and copied into this one)."""
    return not is_original(subdomain, record_id)

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

# Every Person or Note entity belongs to a specific subdomain.  To partition
# the datastore, key names consist of the subdomain, a colon, and then the
# record ID.  Each subdomain appears to be a separate instance of the app
# with its own respository.

# Note that the repository subdomain doesn't necessarily have to match the
# domain in the record ID!  For example, a person record created at
# foo.person-finder.appspot.com would have a key name such as:
#
#     foo:foo.person-finder.appspot.com/person.234
#
# This record would be searchable only at foo.person-finder.appspot.com --
# each repository is independent.  Copying it to bar.person-finder.appspot.com
# would produce a clone record with the key name:
#
#     bar:foo.person-finder.appspot.com/person.234
#
# That is, the clone has the same record ID but a different subdomain.

class Subdomain(db.Model):
    """A separate grouping of Person and Note records.  This is a top-level
    entity, with no parent, whose existence just indicates the existence of
    a subdomain.  Key name: unique subdomain name.  In the UI, each subdomain
    appears to be an independent instance of the application."""
    pass  # No properties for now; only the key_name is significant.


class Base(db.Model):
    """Base class providing methods common to both Person and Note entities,
    whose key names are partitioned using the subdomain as a prefix."""

    # Even though the subdomain is part of the key_name, it is also stored
    # redundantly as a separate property so it can be indexed and queried upon. 
    subdomain = db.StringProperty(required=True)

    # A set of caches, one for each entity kind, to hold entities that have
    # been loaded from the datastore.  Entities that are subclasses of Base
    # should be written only using the create_* methods or by mutating an
    # object obtained through get().  This is necessary for write consistency.
    entity_caches = {}

    @classmethod
    def all_in_subdomain(cls, subdomain):
        """Gets a query for all entities in a given subdomain's repository.
        Callers should treat these entities as read-only; do not mutate and
        put() back entities obtained from this or any other query."""
        return cls.all().filter('subdomain =', subdomain)

    def get_record_id(self):
        """Returns the record ID of this record."""
        subdomain, record_id = self.key().name().split(':', 1)
        return record_id
    record_id = property(get_record_id)

    def get_original_domain(self):
        """Returns the domain name of this record's original repository."""
        return self.record_id.split('/', 1)[0]
    original_domain = property(get_original_domain)

    def is_original(self):
        """Returns True if this record was created in this repository."""
        return is_original(self.subdomain, self.record_id)

    def is_clone(self):
        """Returns True if this record was copied from another repository."""
        return not self.is_original()

    @classmethod
    def get(cls, subdomain, record_id):
        """Gets the entity with the given record_id for a given subdomain.
        If this method is called twice with the same arguments, it is
        guaranteed to return a reference to the same object, so that all
        code sees the same in-memory mutations on any given record."""
        key_name = subdomain + ':' + record_id
        cache = Base.entity_caches.setdefault(cls, {})
        if key_name not in cache:
            cache[key_name] = cls.get_by_key_name(key_name)
        return cache[key_name]

    @classmethod
    def create_original(cls, subdomain, **kwargs):
        """Creates a new original entity with the given field values.  Picks a
        new unique record_id for the new entity.  Calling get() with the same
        subdomain and record_id is guaranteed to return a reference to the same
        object, so that all code sees the same mutations on any given record."""
        record_id = '%s.%s/%s.%d' % (
            subdomain, HOME_DOMAIN, cls.__name__.lower(), UniqueId.create_id())
        key_name = subdomain + ':' + record_id
        cache = Base.entity_caches.setdefault(cls, {})
        cache[key_name] = cls(key_name=key_name, subdomain=subdomain, **kwargs)
        return cache[key_name]

    @classmethod
    def create_clone(cls, subdomain, record_id, **kwargs):
        """Creates a new clone entity with the given field values, using the
        given record_id.  If a record already exists in this subdomain's
        repository with this record_id, it will be replaced when this entity
        is put().  Calling get() with the same subdomain and record_id is
        guaranteed to return a reference to the same object, so that all code
        sees the same mutations on any given record."""
        assert is_clone(subdomain, record_id)
        key_name = subdomain + ':' + record_id
        cache = Base.entity_caches.setdefault(cls, {})
        if key_name in cache:
            for name, value in kwargs.items():
                setattr(cache[key_name], name, value)
        else:
            cache[key_name] = cls(
                key_name=key_name, subdomain=subdomain, **kwargs)
        return cache[key_name]

    @classmethod
    def create_original_with_record_id(cls, subdomain, record_id, **kwargs):
        """Creates an original entity with the given record_id and field
        values, overwriting any existing entity with the same record_id.
        This should be rarely used in practice (e.g. for an administrative
        import into a home repository), hence the long method name.  If a
        record already exists with the given record_id, it will be replaced
        when this entity is put().  Calling get() with the same subdomain
        and record_id is guaranteed to return a reference to the same object,
        so that all code sees the same mutations on any given record."""
        key_name = subdomain + ':' + record_id
        cache = Base.entity_caches.setdefault(cls, {})
        if key_name in cache:
            for name, value in kwargs.items():
                setattr(cache[key_name], name, value)
        else:
            cache[key_name] = cls(
                key_name=key_name, subdomain=subdomain, **kwargs)
        return cache[key_name]


# All fields are either required, or have a default value.  For property
# types that have a false value, the default is the false value.  For types
# with no false value, the default is None.

class Person(Base):
    """The datastore entity kind for storing a PFIF person record.  Never call
    Person() directly; use Person.create_clone() or Person.create_original()."""

    # entry_date should update every time a record is created or re-imported.
    entry_date = db.DateTimeProperty(required=True)

    author_name = db.StringProperty(default='', multiline=True)
    author_email = db.StringProperty(default='')
    author_phone = db.StringProperty(default='')

    # source_date is the original creation time; it should not change.
    source_name = db.StringProperty(default='')
    source_date = db.DateTimeProperty()
    source_url = db.StringProperty(default='')

    first_name = db.StringProperty()
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
    photo_url = db.TextProperty(default='')
    other = db.TextProperty(default='')

    # The following properties are not part of the PFIF data model; they are
    # cached on the Person for efficiency.

    # Value of the latest 'source_date' of all the Notes for this Person.
    latest_note_source_date = db.DateTimeProperty()
    # Value of the 'status' property on the Note with the latest source_date.
    latest_note_status = db.StringProperty()
    # Value of the 'found' property on the Note with the latest source_date.
    latest_note_found = db.BooleanProperty()

    # Last write time of this Person or any related Notes.
    # This reflects any change to the Person page.
    last_modified = db.DateTimeProperty(auto_now=True)

    # attributes used by indexing.py
    names_prefixes = db.StringListProperty()
    _fields_to_index_properties = ['first_name', 'last_name']
    _fields_to_index_by_prefix_properties = ['first_name', 'last_name']

    def get_person_record_id(self):
        return self.record_id
    person_record_id = property(get_person_record_id)

    def get_notes(self, note_limit=200):
        """Retrieves the Notes for this Person."""
        return Note.get_by_person_record_id(
            self.subdomain, self.record_id, limit=note_limit)

    def get_linked_persons(self, note_limit=200):
        """Retrieves the Persons linked (as duplicates) to this Person."""
        linked_persons = []
        for note in self.get_notes(note_limit):
            person = Person.get(self.subdomain, note.linked_person_record_id)
            if person:
                linked_persons.append(person)
        return linked_persons

    def update_from_note(self, note):
        """Updates any necessary fields on the Person to reflect a new Note."""
        # datetime stupidly refuses to compare to None, so we have to check.
        if (self.latest_note_source_date is None or
            note.source_date >= self.latest_note_source_date):
            # Update the Person only with fields actually present in the Note.
            if note.found is not None:  # for boolean, None means unspecified
                self.latest_note_found = note.found
            if note.status:  # for string, '' means unspecified
                self.latest_note_status = note.status
            self.latest_note_source_date = note.source_date

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

    # source_date is the original creation time; it should not change.
    source_date = db.DateTimeProperty()

    status = db.StringProperty(default='', choices=pfif.NOTE_STATUS_VALUES)
    found = db.BooleanProperty()
    email_of_found_person = db.StringProperty(default='')
    phone_of_found_person = db.StringProperty(default='')
    last_known_location = db.StringProperty(default='')
    text = db.TextProperty(default='')

    def get_note_record_id(self):
        return self.record_id
    note_record_id = property(get_note_record_id)

    @staticmethod
    def get_by_person_record_id(subdomain, person_record_id, limit=200):
        """Retrieve notes for a person record, ordered by source_date."""
        query = Note.all_in_subdomain(subdomain)
        query = query.filter('person_record_id =', person_record_id)
        query = query.order('source_date')
        return query.fetch(limit)

    def get_person(self):
        """Fetches the Person entity that this Note is about."""
        return Person.get(self.subdomain, self.person_record_id)

    def get_and_update_person(self):
        """Fetches the Person entity that this Note is about, and updates it."""
        person = self.get_person()
        if person:
            person.update_from_note(self)
        return person


class Photo(db.Model):
    """An entity kind for storing uploaded photos."""
    bin_data = db.BlobProperty()
    date = db.DateTimeProperty(auto_now_add=True)


class Authorization(db.Model):
    """Authorization tokens.  Key name: subdomain + ':' + auth_key."""

    # Even though the subdomain is part of the key_name, it is also stored
    # redundantly as a separate property so it can be indexed and queried upon. 
    subdomain = db.StringProperty(required=True)
    
    # If this field is non-empty, this authorization token allows the client
    # to write records with this original domain.
    domain_write_permission = db.StringProperty()

    # If this flag is true, this authorization token allows the client to read
    # non-sensitive fields (i.e. filtered by utils.filter_sensitive_fields).
    read_permission = db.BooleanProperty()

    # If this flag is true, this authorization token allows the client to read
    # all fields (i.e. not filtered by utils.filter_sensitive_fields).
    full_read_permission = db.BooleanProperty()

    # Bookkeeping information for humans, not used programmatically.
    contact_name = db.StringProperty()
    contact_email = db.StringProperty()
    organization_name = db.StringProperty()

    @classmethod
    def get(cls, subdomain, key):
        """Gets the Authorization entity for a subdomain and key."""
        key_name = subdomain + ':' + key
        return cls.get_by_key_name(key_name)

    @classmethod
    def create(cls, subdomain, key, **kwargs):
        """Creates an Authorization entity for a given subdomain and key."""
        key_name = subdomain + ':' + key
        return cls(key_name=key_name, subdomain=subdomain, **kwargs)


class Secret(db.Model):
    """A place to store application-level secrets in the database."""
    secret = db.BlobProperty()


class Counter(db.Model):
    """Stores a count of the entities of a particular kind."""
    timestamp = db.DateTimeProperty(auto_now=True)
    subdomain = db.StringProperty(required=True)
    kind_name = db.StringProperty(required=True)

    last_key = db.StringProperty(default='')  # if non-empty, count is partial
    count = db.IntegerProperty(default=0)

    @classmethod
    def query_last(cls, subdomain, kind):
        query = cls.all().filter('subdomain =', subdomain)
        query = query.filter('kind_name =', kind.__name__)
        return query.order('-timestamp')

    @classmethod
    def get_count(cls, subdomain, kind):
        cache_key = '%s:count.%s' % (subdomain, kind.__name__)
        count = memcache.get(cache_key)
        if not count:
            # The __key__ index is unreliable and sometimes yields an
            # incorrectly low count.  Work around this by using the
            # maximum of the last few counts.
            query = cls.query_last(subdomain, kind)
            query = query.filter('last_key =', '')
            recent_counters = query.fetch(10)
            count = max([counter.count for counter in recent_counters] + [0])
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
