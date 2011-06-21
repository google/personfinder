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

"""Storage for configuration settings.  Settings can be global or specific
to a subdomain, and their values can be of any JSON-encodable type."""

from google.appengine.ext import db

import UserDict, model, random, simplejson, logging
import datetime, utils
from datetime import timedelta

config_cache = {}
config_cache_expiry_time = {} 
config_cache_miss_count=0
config_cache_hit_count=0
config_cache_evict_count=0
config_cache_items_count=0

class ConfigEntry(db.Model):
    """An application configuration setting, identified by its key_name."""
    value = db.TextProperty(default='')


def get(name, default=None):
    """ Gets a configuration setting. Since 'name' is the key
        to the database, it can be of form 'subdomain:attribute' or
        'attribute'. Two separate functions handle each case """
    split_name = name.split(':',1)
    if split_name[0] == name:
        return get_config_for_global(name, default)
    else:
        return get_config_for_subdomain(split_name[0], split_name[1], default)       
    

def get_or_generate(name):
    """Gets a configuration setting, or sets it to a random 32-byte value
    encoded in hexadecimal if it doesn't exist.  Use this function when you
    need a persistent cryptographic secret unique to the application."""
    random_hex = ''.join('%02x' % random.randrange(256) for i in range(32))
    # Must not retrieve value from cache as it won't differentiate
    # between a non-existant key and a key which exists & who's value is "None"
    entity = ConfigEntry.get_by_key_name(name)
    if entity is None:
        
    ConfigEntry.get_or_insert(key_name=name, value=simplejson.dumps(random_hex))
    return get(name)

def config_cache_invalidate(name)
    """ Delete's the cache entry. 'name' parameter can take two forms
        'subdomain:attribute' or 'attribute'. """
        split_name = name.split(':',1)
        if split_name[0] == name:
            config_cache_delete(name)
        else:
            config_cache_delete(split_name[0])
            sdasf
    #doesn't make sense to do like this
    
def set(**kwargs):
    """Sets configuration settings."""
    db.put(ConfigEntry(key_name=name, value=simplejson.dumps(value))
           for name, value in kwargs.items())


def set_for_subdomain(subdomain, **kwargs):
    """Sets configuration settings for a particular subdomain.  When used
    with get_for_subdomain, has the effect of overriding global settings."""    
    logging.debug("Deleting Subdomain `" + str(subdomain) + "` from config_cache")
    config_cache_delete(subdomain)

    subdomain = str(subdomain)  # need an 8-bit string, not Unicode
    set(**dict((subdomain + ':' + key, value) for key, value in kwargs.items()))

def config_cache_delete(key):
    """Deletes the entry with given key from config_cache """
    global config_cache_items_count
    config_cache_expiry_time.pop(key, None)
    config_cache.pop(key, None)
    config_cache_items_count = config_cache_items_count - 1

def config_cache_add(key, value, time_to_live_in_seconds):
    """ Adds the key/value pair to cache and updates the expiry time.
        If key already exists, its value and expiry are updated """
    global config_cache_items_count        
    config_cache[key] = value
    config_cache_expiry_time[key] = utils.get_utcnow() + timedelta(seconds=time_to_live_in_seconds)
    config_cache_items_count = config_cache_items_count + 1

def config_cache_get(key):
    """ Gets the value corresponding to the key from cache. If cache entry
        has expired, it is deleted from the cache and None is returned. """
    global config_cache_hit_count
    global config_cache_miss_count
    global config_cache_items_count
    global config_cache_evict_count
    
    value = config_cache.get(key)
    if value is None :
        config_cache_miss_count = config_cache_miss_count+1
        return None
    
    now = utils.get_utcnow()
    if ( config_cache_expiry_time[key] > now) :
        config_cache_hit_count = config_cache_hit_count+1
        return value
    else:
        # Stale cache entry. Evicting from cache
        config_cache_expiry_time.pop(key, None)
        config_cache.pop(key, None)
        config_cache_evict_count = config_cache_evict_count + 1
        config_cache_items_count = config_cache_items_count - 1
        config_cache_miss_count = config_cache_miss_count + 1
        return None

def config_cache_stats():
    global config_cache_hit_count
    global config_cache_miss_count
    global config_cache_items_count
    
    print "Hit Count - " + str(config_cache_hit_count)
    print "Miss Count - " + str(config_cache_miss_count)
    print "Items Count - " + str(config_cache_items_count)
    print "Eviction Count - " + str(config_cache_evict_count)
    

def get_config_for_subdomain(subdomain, name, default=None):
    """ Gets the configuration setting for a subdomain. Looks at 
        config_cache first. If entry is not available, get from database.
        NOTE: Subdomain name is used as key for the cache"""
    
    config_data = config_cache_get(subdomain)
    
    if config_data is None:
        # Fetching from database; adding to cache
        logging.debug("Adding Subdomain `" + str(subdomain) + "` to memcache")
        config_entries = model.filter_by_prefix( ConfigEntry.all(), subdomain + ':')
        config_data = dict([(e.key().name().split(':', 1)[1], e) for e in config_entries])  
        config_cache_add(subdomain, config_data, 600)
        
    config_element = config_data.get(name, None)
    
    if config_element is not None:
        return simplejson.loads(config_element.value)
    else :
        return default

def get_config_for_global(name, default=None):
    """ Retrieve global configurations from config_cache, if available. 
        Otherwise get from database. 
        NOTE: Configuration attribute's name is used as key for cache"""
        
    config_element = config_cache_get(name)
    
    if config_element is None:
        # Cache miss, retrieving from database
        logging.debug("Adding global setting `" + str(name) + "` to memcache")
        config_element = ConfigEntry.get_by_key_name(name)        
        if config_element is None:
            # This happens when value for this attribute is not there in the
            # database. This information is cached as a string "no-value" 
            # instead of the python object None.
            config_element="no-value"
        config_cache_add(name, config_element, 600)

    if str(config_element) == "no-value" :
        return default
    else :    
        return simplejson.loads(config_element.value)    



class Configuration(UserDict.DictMixin):
    def __init__(self, subdomain):
        self.subdomain = subdomain

    def __nonzero__(self):
        return True

    def __getattr__(self, name):
        return self[name]

    def __getitem__(self, name):
        """Gets a configuration setting for this subdomain.  Looks for a
        subdomain-specific setting, then falls back to a global setting."""
        value = get_config_for_subdomain(self.subdomain, name) 
        if value is None:
          return get_config_for_global(name)
        return value

        
    def keys(self):
        entries = model.filter_by_prefix(
            ConfigEntry.all(), self.subdomain + ':')
        return [entry.key().name().split(':', 1)[1] for entry in entries]
