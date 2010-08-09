#!/usr/bin/python2.5
# Copyright 2010 Google Inc.
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

"""Command-line utility: imports a site export file into the datastore.

You may want first clear the current datastore before running this;
see http://code.google.com/appengine/docs/python/tools/devserver.html#Using_the_Datastore
for instructions.

Once that's done, with the server running, do

$ scripts/site_export_importer.py path/to/export_file.zip

"""

# import this first to ensure to add necessary paths to find other project
# imports
import remote_api

# python standard library
import logging
import optparse
import pfif
import sys
import StringIO
import zipfile

# personfinder modules
from model import *
import importer


def open_file_inside_zip(zip_path):
  export_zip = zipfile.ZipFile(zip_path)
  entry_count = len(export_zip.infolist())
  if entry_count > 1:
    raise IOError('Zip archive had %d entries, not 1 as expected',
                  entry_count)
  zip_entry = export_zip.infolist()[0]
  logging.info('Reading from zip entry: %s', zip_entry.filename)
  return StringIO.StringIO(export_zip.read(zip_entry.filename))


def next_n(a_list, batch_size):
  """Generator that yields the next batch_size items from a_list."""
  batch = []
  for item in a_list:
    batch.append(item)
    if len(batch) == batch_size:
      yield batch
      batch = []
  if batch:
    yield batch


def maybe_add_required_keys(a_dict, required_keys, dummy_value=u'?'):
  for required_key in required_keys:
    if not importer.strip(a_dict.get(required_key)):
      logging.info(
          '%s is missing from %s; will add dummy value(%s)',
          required_key, a_dict, dummy_value)
      a_dict[required_key] = dummy_value
  return a_dict


def create_person(person_dict):
  try:
    return importer.create_person(person_dict)
  except AssertionError:
    pass
  try:
    person_dict = maybe_add_required_keys(
        person_dict, (u'first_name', u'last_name'))
    return importer.create_person(person_dict)
  except AssertionError:
    logging.info(
          'skipping person %s as it cannot be made valid', person_dict)
    return None


def create_note(note_dict):
  try:
    return importer.create_note(note_dict)
  except AssertionError:
    pass
  try:
    return importer.create_note(note_dict, requires_key=False)
  except AssertionError:
    logging.info(
          'skipping note %s as it cannot be made valid', note_dict)
    return None


def maybe_update_index(entity):
  if hasattr(entity, 'update_index'):
      entity.update_index(['old', 'new'])


def add_entities(entity_dicts, create_function, batch_size, kind, store_all):
  """Adds the data in entity_dicts to storage as entities using create_function.

  Uses next_n to group the entity_dicts into batches which get stored using
  model.db.put(...), after being converted into entities using create_function.

  Args:
    entity_dicts: an iterable of dictionaries containing data to be stored
    create_function: a single arg function: create_function(a_dict) -> an_entity
    batch_size: the size of the batches used to write the entities to storage
    kind: the text name of the entities for logging.
  """
  batch_count = (len(entity_dicts) + batch_size - 1)/batch_size
  for i, batch in enumerate(next_n(entity_dicts, batch_size)):
    entities = [create_function(d) for d in batch]
    entities = [e for e in entities if e]
    for e in entities:
      maybe_update_index(e)
    db.put(entities)
    if i % 10 == 0 or i == batch_count - 1:
      logging.info('%s update: just added batch %d/%d', kind, i + 1,
                   batch_count)

def import_site_export(export_path, remote_api_host,
                       app_id, batch_size, store_all):
  # log in, then use the pfif parser to parse the export file. Use the importer
  # methods to convert the dicts to entities then add them as in import.py, but
  # less strict, to ensure that all exported data is available.
  remote_api.init(app_id, remote_api_host)
  logging.info('%s: importing exported records from %s',
               remote_api_host, export_path)
  if not export_path.endswith('.zip'):
    export_fd = open(export_path)
  else:
    export_fd = open_file_inside_zip(export_path)
  persons, notes = pfif.parse_file(export_fd)
  logging.info('loaded %d persons, %d notes', len(persons), len(notes))
  if not store_all:
    persons = [d for d in persons if
               not importer.is_local_domain(d.get('person_record_id', ''),
                                            'person')]
    notes = [d for d in notes if
             not importer.is_local_domain(d.get('note_record_id', ''),
                                          'note')]
    logging.info('... down to %d persons, %d notes after excluding %s records',
                 len(persons), len(notes), HOME_DOMAIN)
  logging.info('... adding persons')
  add_entities(persons, create_person, batch_size, 'person', store_all)
  logging.info('... adding notes')
  add_entities(notes, create_note, batch_size, 'note', store_all)

def parse_command_line():
  parser = optparse.OptionParser()
  parser.add_option('--import_batch_size',
                    default=100,
                    help='size of batches used during data import')
  parser.add_option('--store_home_domain_records',
                    action='store_true',
                    dest='store_all',
                    default=False,
                    help=('Allows the import of records from the stores home'
                          ' domain.  By default this is disabled because doing'
                          ' so can cause existing records with the same'
                          ' key as an imported record to be overwritten'))
  parser.add_option('--host',
                    default='localhost:8080',
                    help='HOST endpoint to post to for importing data. '
                         '(Required)')
  parser.add_option('--app_id',
                    default='haiticrisis',
                    help='Application ID of endpoint (Optional for '
                         '*.appspot.com)')
  options, args = parser.parse_args()
  if len(args) != 1:
    parser.error('One argument required - the path to the export file')
  return options, args

ARE_YOU_SURE = ('You have specified --store_home_domain_records:\n'
                'This will override records in local storage if there are'
                ' feed records with matching numeric ids.\nContinue? (Y/n) ')

def main():
  logging.basicConfig(level=logging.INFO)
  options, args = parse_command_line()
  export_path = args[0]
  if options.store_all:
    answer = raw_input(ARE_YOU_SURE)
    if answer and answer[0] in ('n', 'N'):
      logging.info("... exiting")
      sys.exit(0)
  import_site_export(
      export_path, options.host, options.app_id,
      options.import_batch_size, options.store_all)


if __name__ == '__main__':
  main()
