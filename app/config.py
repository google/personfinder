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
    """ Gets a configuration setting. 'name' can have be 
        of form 'subdomain:attribute' or 'attribute'.
        Prefixing with '*' for global config names""" 
    split_name = name.split(':',1)
    if split_name[0] == name:
        return get_configuration('*', name, default)
    else:
        return get_configuration(split_name[0], split_name[1], default)       
        
def set(**kwargs):
    """Sets configuration settings."""
    ### This function is used at one place in tools/setup.py. 
    ### Use this to set configurations for global domain only
    set_for_subdomain('*', **kwargs)
    

def set_for_subdomain(subdomain, **kwargs):
    """Sets configuration settings for a particular subdomain.  When used
    with get_for_subdomain, has the effect of overriding global settings."""    
    subdomain = str(subdomain)  # need an 8-bit string, not Unicode
    for key, value in kwargs.items():
        temp = simplejson.dumps(value)
        db.put( ConfigEntry(key_name=subdomain + ':' + key, value= temp) )
        config_cache_modify_data(subdomain, key, temp)

def config_cache_modify_data(subdomain, key, value):
    """ Modifies the contents of cache entry to add/update the
        key and value. If the cache entry does not exist, it 
        doesn't do anything. Also, this doesn't reset the expiry time. """
    entry = config_cache.get(subdomain, None)    
    if entry is not None:
        entry[key] = value
        
    
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

def config_cache_retrieve(key):
    """ Gets the value corresponding to the key from cache. If cache entry
        has expired, it is deleted from the cache and None is returned.
        If the cache entry for that key does not exist, it returns a string
        'key-not-present' instead of python object None. This is because 
        some attributes could actually have the value None which has to be
        differentiated from a non-existant key. """
    global config_cache_hit_count
    global config_cache_miss_count
    global config_cache_items_count
    global config_cache_evict_count
    
    value = config_cache.get(key, None)
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
    

def get_for_subdomain(subdomain, name, default=None):
    """ A dummy function for backward compatability """
    get_configuration(subdomain, name, default=None)

def get_configuration(subdomain, name, default=None):
    """ Gets the configuration setting for a subdomain. Looks at 
        config_cache first. If entry is not available, get from database.
        NOTE: Subdomain name is used as key for the cache"""

    config_data = config_cache_retrieve(subdomain)
    
    if config_data is None:
        # Cache miss; retrieving from database
        entries = model.filter_by_prefix( ConfigEntry.all(), subdomain + ':')
        if entries is None:
            # Config for subdomain does not exist
            return default 
        logging.debug("Adding Subdomain `" + str(subdomain) + "` to config_cache")
        config_data = dict([(e.key().name().split(':', 1)[1], e.value) for e in entries])  
        config_cache_add(subdomain, config_data, 600)
    
    element = config_data.get(name)
    if element is None:
        return default
    else:
        return simplejson.loads(element)
    
    
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
        value = get_configuration(self.subdomain , name) 
        if value is None:
          return get_configuration('*', name)
        return value

        
    def keys(self):
        entries = model.filter_by_prefix(
            ConfigEntry.all(), self.subdomain + ':')
        return [entry.key().name().split(':', 1)[1] for entry in entries]
