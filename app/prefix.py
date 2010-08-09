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

"""Support for approximate string prefix queries."""

__author__ = 'kpy@google.com (Ka-Ping Yee)'

from google.appengine.ext import db
import unicodedata

def normalize(string):
  """Normalize a string to all uppercase and remove accents."""
  string = unicode(string or '').strip().upper()
  decomposed = unicodedata.normalize('NFD', string)
  return ''.join(ch for ch in decomposed if unicodedata.category(ch) != 'Mn')

def add_prefix_properties(model_class, *properties):
  """Adds indexable properties to a model class to support prefix queries.
  All properties ending in '_' are extra properties.  The 'properties'
  arguments should be names of existing string properties on the class."""
  for property in properties:
    # This property contains a copy of the entire string normalized.
    setattr(model_class, property + '_n_', db.StringProperty())

    # This property contains just the first character, normalized.
    setattr(model_class, property + '_n1_', db.StringProperty())

    # This property contains just the first two characters, normalized.
    setattr(model_class, property + '_n2_', db.StringProperty())

  # Record the prefix properties.
  if not hasattr(model_class, '_prefix_properties'):
    model_class._prefix_properties = []
  model_class._prefix_properties += list(properties)

  # Update the model class.
  db._initialize_properties(
      model_class, model_class.__name__, model_class.__bases__,
      model_class.__dict__)

def update_prefix_properties(entity):
  """Finds and updates all prefix-related properties on the given entity."""
  if hasattr(entity, '_prefix_properties'):
    for property in entity._prefix_properties:
      value = normalize(getattr(entity, property))
      setattr(entity, property + '_n_', value)
      setattr(entity, property + '_n1_', value[:1])
      setattr(entity, property + '_n2_', value[:2])

def filter_prefix(query, **kwargs):
  """Approximately filters a query for the given prefix strings.  Each keyword
  argument should specify a desired normalized prefix for a string property."""
  for property, prefix in kwargs.items():
    prefix = normalize(prefix)
    if len(prefix) >= 2:
      query = query.filter(property + '_n2_ =', prefix[:2])
    elif len(prefix) == 1:
      query = query.filter(property + '_n1_ =', prefix[:1])
  return query

def get_prefix_matches(query, limit, **kwargs):
  """Scans the results from a given query, yielding only those which actually
  match the given normalized prefixes.  Each keyword argument should specify
  a desired normalized prefix for a string property."""
  for entity in query:
    for property, prefix in kwargs.items():
      value = normalize(getattr(entity, property))
      if not value.startswith(normalize(prefix)):
        break
    else:
      yield entity
      limit -= 1
      if limit == 0:
        return
