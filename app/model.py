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

from google.appengine.api import datastore_errors
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

    @classmethod
    def all_in_subdomain(cls, subdomain):
        """Gets a query for all entities in a given subdomain's repository."""
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
        """Gets the entity with the given record_id in a given repository."""
        return cls.get_by_key_name(subdomain + ':' + record_id)

    @classmethod
    def create_original(cls, subdomain, **kwargs):
        """Creates a new original entity with the given field values."""
        record_id = '%s.%s/%s.%d' % (
            subdomain, HOME_DOMAIN, cls.__name__.lower(), UniqueId.create_id())
        key_name = subdomain + ':' + record_id
        return cls(key_name=key_name, subdomain=subdomain, **kwargs)

    @classmethod
    def create_clone(cls, subdomain, record_id, **kwargs):
        """Creates a new clone entity with the given field values."""
        assert is_clone(subdomain, record_id)
        key_name = subdomain + ':' + record_id
        return cls(key_name=key_name, subdomain=subdomain, **kwargs)

    @classmethod
    def create_original_with_record_id(cls, subdomain, record_id, **kwargs):
        """Creates an original entity with the given record_id and field
        values, overwriting any existing entity with the same record_id.
        This should be rarely used in practice (e.g. for an administrative
        import into a home repository), hence the long method name."""
        key_name = subdomain + ':' + record_id
        return cls(key_name=key_name, subdomain=subdomain, **kwargs)


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

    # Value of the 'status' and 'source_date' properties on the Note
    # with the latest source_date with the 'status' field present.
    latest_status = db.StringProperty(default='')
    latest_status_source_date = db.DateTimeProperty()
    # Value of the 'found' and 'source_date' properties on the Note
    # with the latest source_date with the 'found' field present.
    latest_found = db.BooleanProperty()
    latest_found_source_date = db.DateTimeProperty()

    # Last write time of this Person or any Notes on this Person.
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
        # We want to transfer only the *non-empty, newer* values to the Person.
        if note.found is not None:  # for boolean, None means unspecified
            # datetime stupidly refuses to compare to None, so check for None.
            if (self.latest_found_source_date is None or
                note.source_date >= self.latest_found_source_date):
                self.latest_found = note.found
                self.latest_found_source_date = note.source_date
        if note.status:  # for string, '' means unspecified
            if (self.latest_status_source_date is None or
                note.source_date >= self.latest_status_source_date):
                self.latest_status = note.status
                self.latest_status_source_date = note.source_date

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

    # True if the note has been marked as spam. Will cause the note to be
    # initially hidden from display upon loading a record page.
    hidden = db.BooleanProperty(default=False)

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


class Counter(db.Expando):
    """Counters hold partial and completed results for ongoing counting tasks.
    To see how this is used, check out tasks.py.  A single Counter object can
    contain several named accumulators.  Typical usage is to scan for entities
    in order by __key__, update the accumulators for each entity, and save the
    partial counts when the time limit for a request is reached.  The last
    scanned key is saved in last_key so the next request can pick up the scan
    where the last one left off.  A non-empty last_key means a scan is not
    finished; when a scan is done, last_key should be set to ''."""
    timestamp = db.DateTimeProperty(auto_now=True)
    scan_name = db.StringProperty()
    subdomain = db.StringProperty()
    last_key = db.StringProperty(default='')  # if non-empty, count is partial

    # Each Counter also has a dynamic property for each accumulator; all such
    # properties are named "count_" followed by a count_name.

    def get(self, count_name):
        """Gets the specified accumulator from this counter object."""
        return getattr(self, 'count_' + count_name, 0)

    def increment(self, count_name):
        """Increments the given accumulator on this Counter object."""
        prop_name = 'count_' + count_name
        setattr(self, prop_name, getattr(self, prop_name, 0) + 1)

    @classmethod
    def get_count(cls, subdomain, name):
        """Gets the latest finished count for the given subdomain and name.
        'name' should be in the format scan_name + '.' + count_name."""
        scan_name, count_name = name.split('.')
        counter_key = subdomain + ':' + scan_name

        # Get the counts from memcache, loading from datastore if necessary.
        counter_dict = memcache.get(counter_key)
        if not counter_dict:
            try:
                # Get the latest completed counter with this scan_name.
                counter = cls.all().filter('subdomain =', subdomain
                                  ).filter('scan_name =', scan_name
                                  ).filter('last_key =', ''
                                  ).order('-timestamp').get()
            except datastore_errors.NeedIndexError:
                # Absurdly, it can take App Engine up to an hour to build an
                # index for a kind that has zero entities, and during that time
                # all queries fail.  Catch this error so we don't get screwed.
                counter = None

            counter_dict = {}
            if counter:
                # Cache the counter's contents in memcache for one minute.
                counter_dict = dict((name[6:], getattr(counter, name))
                                    for name in counter.dynamic_properties()
                                    if name.startswith('count_'))
                memcache.set(counter_key, counter_dict, 60)

        # Get the count for the given count_name.
        return counter_dict.get(count_name, 0)

    @classmethod
    def all_finished_counters(cls, subdomain, scan_name):
        """Gets a query for all finished counters for the specified scan."""
        return cls.all().filter('subdomain =', subdomain
                       ).filter('scan_name =', scan_name
                       ).filter('last_key =', '')

    @classmethod
    def get_unfinished_or_create(cls, subdomain, scan_name):
        """Gets the latest unfinished Counter entity for the given subdomain
        and scan_name.  If there is no unfinished Counter, create a new one."""
        counter = cls.all().filter('subdomain =', subdomain
                          ).filter('scan_name =', scan_name
                          ).order('-timestamp').get()
        if not counter or not counter.last_key:
            counter = Counter(subdomain=subdomain, scan_name=scan_name)
        return counter

class NoteFlag(db.Model):
    """Tracks spam / abuse changes to notes."""
    subdomain = db.StringProperty(required=True)
    note_record_id = db.StringProperty(required=True)
    time = db.DateTimeProperty(required=True)
    # True if the note is being marked as spam,
    # False if being marked as not spam
    spam = db.BooleanProperty(required=True)
    reason_for_report = db.StringProperty()

class PersonFlag(db.Model):
    """Tracks deletion of person records."""
    subdomain = db.StringProperty(required=True)
    time = db.DateTimeProperty(required=True)
    reason_for_deletion = db.StringProperty(required=True)

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
