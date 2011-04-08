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

def get_properties_as_dict(db_obj):
    """Returns a dictionary containing all (dynamic)* properties of db_obj."""
    properties = dict((k, v.__get__(db_obj, db_obj.__class__)) for
                      k, v in db_obj.properties().iteritems() if
                      v.__get__(db_obj, db_obj.__class__))
    dynamic_properties = dict((prop, getattr(db_obj, prop)) for
                              prop in db_obj.dynamic_properties())
    properties.update(dynamic_properties)
    return properties

def clone_to_new_type(origin, dest_class, **kwargs):
    """Clones the given entity to a new entity of the type "dest_class".
    Optionally, pass in values to kwargs to update values during cloning."""
    vals = get_properties_as_dict(origin)
    vals.update(**kwargs)
    if hasattr(origin, 'record_id'):
        vals.update(record_id=origin.record_id)
    return dest_class(key_name=origin.key().name(), **vals)

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
    # No properties for now; only the key_name is significant.

    @classmethod
    def list(cls):
        return [subdomain.key().name() for subdomain in cls.all()]


class Base(db.Model):
    """Base class providing methods common to both Person and Note entities,
    whose key names are partitioned using the subdomain as a prefix."""

    # Even though the subdomain is part of the key_name, it is also stored
    # redundantly as a separate property so it can be indexed and queried upon.
    subdomain = db.StringProperty(required=True)

    # We can't use an inequality filter on expiry_date (together with other
    # inequality filters), so we use a periodic task to set the is_expired flag
    # on expired records, and filter using the flag.  A record's life cycle is:
    #
    # 1. Record is created with some expiry_date.
    # 2. expiry_date passes.
    # 3. tasks.DeleteExpired sets is_expired to True; record vanishes from UI.
    # 4. delete.EXPIRED_TTL_DAYS days pass.
    # 5. tasks.DeleteExpired wipes the record.
    
    # We set default=False to ensure all entities are indexed by is_expired.
    # NOTE: is_expired should ONLY be modified in Person.put_expiry_flags().
    is_expired = db.BooleanProperty(required=False, default=False)

    @classmethod
    def all(cls, keys_only=False, filter_expired=True):
        """Returns a query for all records of this kind; by default this
        filters out the records marked as expired.
        
        Args:
          keys_only - If true, return only the keys.  
          filter_expired - If true, omit records with is_expired == True.
        Returns:
          query - A Query object for the results.
        """
        query = super(Base, cls).all(keys_only=keys_only)
        if filter_expired:
            query.filter('is_expired =', False)
        return query

    @classmethod
    def all_in_subdomain(cls, subdomain, filter_expired=True):
        """Gets a query for all entities in a given subdomain's repository."""
        return cls.all(filter_expired=filter_expired).filter(
            'subdomain =', subdomain)

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
    def get_key(cls, subdomain, record_id):
        """Get entity key from its record id"""
        return db.Key.from_path(cls.kind(), subdomain + ':' + record_id)

    @classmethod
    def get_all(cls, subdomain, record_ids, limit=200):
        """Gets the entities with the given record_ids in a given repository."""
        keys = [cls.get_key(subdomain, id) for id in record_ids]
        return [record for record in db.get(keys) if record is not None]

    @classmethod
    def get(cls, subdomain, record_id, filter_expired=True):
        """Gets the entity with the given record_id in a given repository."""
        record = cls.get_by_key_name(subdomain + ':' + record_id)
        if record:
            if not (filter_expired and record.is_expired):
                return record

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

    # TODO(kpy): Rename this function (maybe to create_with_record_id?).
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
    Person() directly; use Person.create_clone() or Person.create_original().

    Methods that start with "get_" return actual values or lists of values;
    other methods return queries or generators for values.
    """
    # If you add any new fields, be sure they are handled in wipe_contents().

    # entry_date should update every time a record is created or re-imported.
    entry_date = db.DateTimeProperty(required=True)
    expiry_date = db.DateTimeProperty(required=False)

    author_name = db.StringProperty(default='', multiline=True)
    author_email = db.StringProperty(default='')
    author_phone = db.StringProperty(default='')

    # source_date is the original creation time; it should not change.
    source_name = db.StringProperty(default='')
    source_date = db.DateTimeProperty()
    source_url = db.StringProperty(default='')

    full_name = db.StringProperty()
    first_name = db.StringProperty()
    last_name = db.StringProperty()
    # alternate_{first|last}_name field may contain any additional names that do
    # not fit into first_name or last_name.  What those additional names mean
    # varies across languages (e.g. in Japanese, users are directed to input
    # readings (phonetic representations) of their names.)
    alternate_first_names = db.StringProperty(default='')
    alternate_last_names = db.StringProperty(default='')
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


    # This reference points to a locally stored Photo entity.  ONLY set this
    # property when storing a new Photo object that is owned by this Person
    # record and can be safely deleted when the Person is deleted.
    photo = db.ReferenceProperty(default=None)
    

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

    @staticmethod
    def past_due_records():
        """Returns a query for all Person records with expiry_date in the past,
        regardless of their is_expired flags."""
        import utils
        return Person.all(filter_expired=False).filter(
            'expiry_date <=', utils.get_utcnow())

    def get_person_record_id(self):
        return self.record_id
    person_record_id = property(get_person_record_id)

    def get_notes(self, filter_expired=True):
        """Returns a list of all the Notes on this Person, omitting expired
        Notes by default."""
        return Note.get_by_person_record_id(
            self.subdomain, self.record_id, filter_expired=filter_expired)

    def get_subscriptions(self, subscription_limit=200):
        """Retrieves a list of all the Subscriptions for this Person."""
        return Subscription.get_by_person_record_id(
            self.subdomain, self.record_id, limit=subscription_limit)

    def get_linked_person_ids(self, note_limit=200):
        """Retrieves IDs of Persons marked as duplicates of this Person."""
        return [note.linked_person_record_id
                for note in self.get_notes(note_limit)
                if note.linked_person_record_id]

    def get_linked_persons(self, note_limit=200):
        """Retrieves Persons marked as duplicates of this Person."""
        return Person.get_all(self.subdomain,
                              self.get_linked_person_ids(note_limit))

    def get_all_linked_persons(self):
        """Retrieves all Persons transitively linked to this Person."""
        linked_person_ids = set([self.record_id])
        linked_persons = []
        # Maintain a list of ids of duplicate persons that have not
        # yet been processed.
        new_person_ids = set(self.get_linked_person_ids())
        # Iteratively process all new_person_ids by retrieving linked
        # duplicates and storing those not yet processed.
        # Processed ids are stored in the linked_person_ids set, and
        # their corresponding records are in the linked_persons list.
        while new_person_ids:
            linked_person_ids.update(new_person_ids)
            new_persons = Person.get_all(self.subdomain, list(new_person_ids))
            for person in new_persons:
                new_person_ids.update(person.get_linked_person_ids())
            linked_persons += new_persons
            new_person_ids -= linked_person_ids
        return linked_persons

    def get_associated_emails(self):
        """Gets a set of all the e-mail addresses to notify when this record 
        is changed."""
        email_addresses = set([note.author_email for note in self.get_notes()
                               if note.author_email])
        if self.author_email:
            email_addresses.add(self.author_email)
        return email_addresses

    def put_expiry_flags(self):
        """Updates the is_expired flags on this Person and related Notes to
        make them consistent with the expiry_date on this Person, and commits
        these changes to the datastore."""
        import utils
        now = utils.get_utcnow()
        expired = self.expiry_date and now >= self.expiry_date
        if self.is_expired != expired:
            # NOTE: This should be the ONLY code that modifies is_expired.
            self.is_expired = expired

            # If the record is expiring (being replaced with a placeholder,
            # see http://zesty.ca/pfif/1.3/#data-expiry) or un-expiring (being 
            # restored from deletion), we want the source_date and entry_date
            # updated so downstream clients will see this as the newest state.
            self.source_date = now
            self.entry_date = now

            # All the Notes on the Person also expire or unexpire, to match.
            notes = self.get_notes(filter_expired=False)
            for note in notes:
                note.is_expired = expired

            # Store these changes in the datastore.
            db.put(notes + [self])
            # TODO(lschumacher): photos don't have expiration currently.

    def wipe_contents(self):
        """Sets all the content fields to None (leaving timestamps and the
        expiry flag untouched), stores the empty record, and permanently
        deletes any related Notes and Photo.  Call this method ONLY on records
        that have already expired."""

        # We rely on put_expiry_flags to have properly set the source_date,
        # entry_date, and is_expired flags on Notes, as necessary.
        assert self.is_expired

        # Delete all related Notes (they will have is_expired == True by now).
        db.delete(self.get_notes(filter_expired=False))
        if self.photo:
            db.delete(self.photo)  # Delete the locally stored Photo, if any.

        for name, property in self.properties().items():
            # Leave the subdomain, is_expired flag, and timestamps untouched.
            if name not in ['subdomain', 'is_expired',
                            'source_date', 'entry_date', 'expiry_date']:
                setattr(self, name, property.default)
        self.put()  # Store the empty placeholder record.

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

    FETCH_LIMIT = 200

    # The entry_date should update every time a record is re-imported.
    entry_date = db.DateTimeProperty(required=True)

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

    # True if the note has been reviewed for spam content at /admin/review.
    reviewed = db.BooleanProperty(default=False)

    def get_note_record_id(self):
        return self.record_id
    note_record_id = property(get_note_record_id)
    
    @staticmethod
    def get_by_person_record_id(
        subdomain, person_record_id, filter_expired=True):
        """Gets a list of all the Notes on a Person, ordered by source_date."""
        return list(Note.generate_by_person_record_id(
            subdomain, person_record_id, filter_expired))

    @staticmethod
    def generate_by_person_record_id(
        subdomain, person_record_id, filter_expired=True):
        """Generates all the Notes on a Person record ordered by source_date."""
        query = Note.all_in_subdomain(subdomain, filter_expired=filter_expired
            ).filter('person_record_id =', person_record_id
            ).order('source_date')
        notes = query.fetch(Note.FETCH_LIMIT)
        while notes:
            for note in notes:
                yield note
            query.with_cursor(query.cursor())  # Continue where fetch left off.
            notes = query.fetch(Note.FETCH_LIMIT)


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

    # If this flag is true, this authorization token allows the client to use
    # the search API and return non-sensitive fields (i.e. filtered
    # by utils.filter_sensitive_fields).
    search_permission = db.BooleanProperty()

    # If this flag is true, this authorization token allows the client to use
    # the API to subscribe any e-mail address to updates on any person.
    subscribe_permission = db.BooleanProperty()

    # If this flag is true, notes written with this authorization token are
    # marked as "reviewed" and won't show up in admin's review list.
    mark_notes_reviewed = db.BooleanProperty()

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

def encode_count_name(count_name):
    """Encode a name to printable ASCII characters so it can be safely
    used as an attribute name for the datastore."""
    encoded = []
    append = encoded.append
    for ch in map(ord, count_name):
        if ch == 92:
            append('\\\\')
        elif 33 <= ch <= 126:
            append(chr(ch))
        else:
            append('\\u%04x' % ch)
    return ''.join(encoded)

class ApiActionLog(db.Model):
    """Log of api key usage."""
    # actions
    DELETE = 'delete'
    READ = 'read'
    SEARCH = 'search'
    WRITE = 'write'
    SUBSCRIBE = 'subscribe'    
    UNSUBSCRIBE = 'unsubscribe'
    ACTIONS = [DELETE, READ, SEARCH, WRITE, SUBSCRIBE, UNSUBSCRIBE]

    subdomain = db.StringProperty(required=True)
    api_key = db.StringProperty()
    action = db.StringProperty(required=True, choices=ACTIONS)
    person_records = db.IntegerProperty()
    note_records = db.IntegerProperty()
    people_skipped = db.IntegerProperty() # write only
    notes_skipped = db.IntegerProperty() # write only
    user_agent = db.StringProperty()
    ip_address = db.StringProperty() # client ip
    request_url = db.StringProperty()
    version = db.StringProperty() # pfif version.
    timestamp = db.DateTimeProperty(auto_now=True)

    @staticmethod
    def record_action(subdomain, api_key, version, action, person_records,
                      note_records, people_skipped, notes_skipped, user_agent,
                      ip_address, request_url,
                      timestamp=None):
        import utils
        ApiActionLog(subdomain=subdomain,
                  api_key=api_key,
                  action=action,
                  person_records=person_records,
                  note_records=note_records,
                  people_skipped=people_skipped,
                  notes_skipped=notes_skipped,
                  user_agent=user_agent,
                  ip_address=ip_address,
                  request_url=request_url,
                  version=version,
                  timestamp=timestamp or utils.get_utcnow()).put()

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
    # properties are named "count_" followed by a count_name.  The count_name
    # is encoded to ensure all its characters are printable ASCII.
    def get(self, count_name):
        """Gets the specified accumulator from this counter object."""
        return getattr(self, 'count_' + encode_count_name(count_name), 0)

    def increment(self, count_name):
        """Increments the given accumulator on this Counter object."""
        prop_name = 'count_' + encode_count_name(count_name)
        setattr(self, prop_name, getattr(self, prop_name, 0) + 1)

    @classmethod
    def get_count(cls, subdomain, name):
        """Gets the latest finished count for the given subdomain and name.
        'name' should be in the format scan_name + '.' + count_name."""
        scan_name, count_name = name.split('.')
        count_name = encode_count_name(count_name)
        return cls.get_all_counts(subdomain, scan_name).get(count_name, 0)

    @classmethod
    def get_all_counts(cls, subdomain, scan_name):
        """Gets a dictionary of all the counts for the last completed scan
        for the given subdomain and scan name."""
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

        # Return the dictionary of counts for this scan.
        return counter_dict

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


class Subscription(db.Model):
    """Subscription to notifications when a note is added to a person record"""
    subdomain = db.StringProperty(required=True)
    person_record_id = db.StringProperty(required=True)
    email = db.StringProperty(required=True)
    language = db.StringProperty(required=True)
    timestamp = db.DateTimeProperty(auto_now_add=True)

    @staticmethod
    def create(subdomain, record_id, email, language):
        """Creates a new Subscription"""
        key_name = '%s:%s:%s' % (subdomain, record_id, email)
        return Subscription(key_name=key_name, subdomain=subdomain,
                            person_record_id=record_id,
                            email=email, language=language)

    @staticmethod
    def get(subdomain, record_id, email):
        """Gets the entity with the given record_id in a given repository."""
        key_name = '%s:%s:%s' % (subdomain, record_id, email)
        return Subscription.get_by_key_name(key_name)

    @staticmethod
    def get_by_person_record_id(subdomain, person_record_id, limit=200):
        """Retrieve subscriptions for a person record."""
        query = Subscription.all().filter('subdomain =', subdomain)
        query = query.filter('person_record_id =', person_record_id)
        return query.fetch(limit)


class UserActionLog(db.Expando):
    """Logs user actions."""
    time = db.DateTimeProperty(required=True)
    action = db.StringProperty(required=True, choices=[
        'delete', 'restore', 'hide', 'unhide', 'mark_dead', 'mark_alive'])
    entity_kind = db.StringProperty(required=True)
    entity_key_name = db.StringProperty(required=True)
    detail = db.TextProperty()
    ip_address = db.StringProperty()

    @classmethod
    def put_new(cls, action, entity, detail='', ip_address=''):
        """Adds an entry to the UserActionLog.  'action' is the action that
        the user performed, 'entity' is the entity that was operated on, and
        'detail' is a string containing any other details."""
        import utils
        kind = entity.kind()
        entry = cls(
            time=utils.get_utcnow(), action=action, entity_kind=kind,
            entity_key_name=entity.key().name(), detail=detail,
            ip_address=ip_address)
        for name in entity.properties():  # copy the properties of the entity
            value = getattr(entity, name)
            if isinstance(value, db.Model):
                value = value.key()
            setattr(entry, kind + '_' + name, value)
        entry.put()


class UserAgentLog(db.Model):
    """Logs information about the user agent."""
    timestamp = db.DateTimeProperty(auto_now=True)
    subdomain = db.StringProperty()
    user_agent = db.StringProperty()
    lang = db.StringProperty()
    accept_charset = db.StringProperty()
    ip_address = db.StringProperty()
    sample_rate = db.FloatProperty()


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
