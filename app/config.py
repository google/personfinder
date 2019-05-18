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

"""Storage for configuration settings.  Settings can be global or specific
to a repository, and their values can be of any JSON-encodable type.

See here for usage examples:
https://github.com/google/personfinder/wiki/DeveloperFaq
"""

from google.appengine.ext import db
import UserDict, model, random, simplejson
import logging
import datetime
import utils
from datetime import timedelta


class ConfigurationCache:
    """This class implements an in-memory cache used to store the config
    entries. Cache entries have a default lifetime of 600 seconds. When
    fetching a config entry, the cache is first searched. If the entry is
    not available in cache it is retrieved from database, added to cache and
    returned. Cache is enabled by setting a config entry *:config_cache_enable.
    Config entries are stored with the key repo:entry_name in database.
    This cache uses the repo as the key and stores all configs for a
    repository in one cache element. The global configs have repo='*'."""
    storage = {}
    expiry_time = 600
    miss_count = 0
    hit_count = 0
    evict_count = 0
    items_count = 0
    max_items = 0

    def flush(self):
        self.storage.clear()
        self.items_count=0

    def delete(self,key):
        """Deletes the entry with given key from config_cache."""
        if key in self.storage:
            self.storage.pop(key)
            self.items_count -= 1

    def add(self, key, value, time_to_live_in_seconds):
        """Adds the key/value pair to cache and updates the expiry time.
           If key already exists, its value and expiry are updated."""
        expiry = utils.get_utcnow() + timedelta(seconds=time_to_live_in_seconds)
        self.storage[key] = (value, expiry)
        self.items_count += 1
        self.max_items += 1

    def read(self, key, default=None):
        """Gets the value corresponding to the key from cache. If cache entry
           has expired, it is deleted from the cache and None is returned."""
        value, expiry = self.storage.get(key, (None, 0))
        if value is None :
            self.miss_count += 1
            return default

        now = utils.get_utcnow()
        if (expiry > now) :
            self.hit_count += 1
            return value
        else:
            # Stale cache entry. Evicting from cache
            self.delete(key)
            self.evict_count += 1
            self.miss_count += 1
            return default

    def stats(self):
        logging.info("Hit Count - %r" % self.hit_count)
        logging.info("Miss Count - %r" % self.miss_count)
        logging.info("Items Count - %r" % self.items_count)
        logging.info("Eviction Count - %r" % self.evict_count)
        logging.info("Max Items - %r" % self.max_items)

    def get_config(self, repo, name, default=None):
        """Looks for data in cache. If not present, retrieves from
           database, stores it in cache and returns the required value."""
        config_dict = self.read(repo, None)
        if config_dict is None:
            # Cache miss
            entries = model.filter_by_prefix(ConfigEntry.all(), repo + ':')
            if entries is None:
                return default
            logging.debug("Adding repository %r to config_cache" % repo)
            config_dict = dict([(e.key().name().split(':', 1)[1],
                         simplejson.loads(e.value)) for e in entries])
            self.add(repo, config_dict, self.expiry_time)

        if name in config_dict:
            return config_dict[name]
        return default

    def enable(self, value):
        """Enable/disable caching of config."""
        logging.info('Setting config_cache_enable to %s' % value)
        db.put(ConfigEntry(key_name="*:config_cache_enable",
                           value=simplejson.dumps(bool(value))))
        self.delete('*')

    def is_enabled(self):
        return self.get_config('*', 'config_cache_enable', None)

cache = ConfigurationCache()


class ConfigEntry(db.Model):
    """An application configuration setting, identified by its key_name."""
    value = db.TextProperty(default='')


# If calling from code where a Configuration object is available (e.g., from
# within a handler), prefer Configuration.get. Configuration objects get all
# config entries when they're initialized, so they don't need to make an
# additional Datastore query.
def get(name, default=None, repo='*'):
    """Gets a configuration setting from cache if it is enabled,
       otherwise from the database."""
    if cache.is_enabled():
        return cache.get_config(repo, name, default)
    entry = ConfigEntry.get_by_key_name(repo + ':' + name)
    if entry:
        return simplejson.loads(entry.value)
    return default

def set(repo='*', **kwargs):
    """Sets configuration settings."""
    if 'launched_repos' in kwargs.keys():
        raise Exception(
            'Config "launched_repos" is deprecated. Use per-repository '
            'config "launched" instead.')
    db.put(ConfigEntry(key_name=repo + ':' + name,
           value=simplejson.dumps(value)) for name, value in kwargs.items())
    cache.delete(repo)

# If calling from code where a Configuration object is available (e.g., from
# within a handler), prefer Configuration.get. Configuration objects get all
# config entries when they're initialized, so they don't need to make an
# additional Datastore query.
def get_for_repo(repo, name, default=None):
    """Gets a configuration setting for a particular repository.  Looks for a
    setting specific to the repository, then falls back to a global setting."""
    NOT_FOUND = []  # a unique sentinel distinct from None
    value = get(name, NOT_FOUND, repo)
    if value is NOT_FOUND:
        value = get(name, default, '*')
    return value

def set_for_repo(repo, **kwargs):
    """Sets configuration settings for a particular repository.  When used
    with get_for_repo, has the effect of overriding global settings."""
    set(str(repo), **kwargs)


class Configuration(UserDict.DictMixin):
    def __init__(self, repo, include_global=True):
        self.repo = repo
        # We fetch all the config entries at once here, so that we don't have to
        # make many Datastore queries for each individual entry later.
        db_entries = model.filter_by_prefix(
            ConfigEntry.all(), self.repo + ':')
        self.entries = {
            entry.key().name().split(':', 1)[1]: simplejson.loads(entry.value)
            for entry in db_entries
        }
        if include_global:
            self.global_config = None if repo == '*' else Configuration('*')
        else:
            self.global_config = None

    def __nonzero__(self):
        return True

    def __getattr__(self, name):
        if name == '__call__':
            # A Configuration instance must not be callable.
            # i.e., callable(c) must be False for a Configuration instance c.
            # Otherwise writing config.xxx in Django template doesn't work as
            # expected because it interprets the expression as config().xxx.
            raise AttributeError('Configuration is not callable')
        else:
            return self[name]

    def __getitem__(self, name):
        """Gets a configuration setting for this repository.  Looks for a
        repository-specific setting, then falls back to a global setting."""
        if name in self.entries:
            return self.entries[name]
        elif self.global_config:
            return self.global_config[name]
        return None

    def get(self, name, default=None):
        # UserDict.DictMixin.get isn't going to do what we want, because it only
        # returns the default if __getitem__ raises an exception (which ours
        # never does).
        res = self[name]
        if res is None:
            return default
        return res

    def keys(self):
        return self.entries.keys()
