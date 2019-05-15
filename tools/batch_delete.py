# Copyright 2017 Google Inc.
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

"""A script to delete entities in AppEngine data store in batch.

Instead of running this script directly, use the 'batch_delete' shell script,
which sets up the PYTHONPATH and other necessary environment variables."""
from __future__ import print_function

import optparse

from google.appengine.ext import db

import model
import remote_api


def main():
    parser = optparse.OptionParser(usage='''tools/batch_delete [options]

Delete entities in AppEngine data store in batch.

It can be used in case any manual clean up is needed. Use it with care.

Example:

    This command line performs a *preview* i.e., it shows sample entities to be
    deleted without actually deleting them:

    $ tools/batch_delete \\
      --url=xyz.appspot.com \\
      --gql-query="select * from Person where repo='test'" \\
      --mode=preview

    Confirm the output and replace --mode=preview with --mode=delete to actually
    delete them.
''')
    parser.add_option('--url',
                      dest='url',
                      help='The AppEngine server URL to connect to. See the '
                           'comment in console.py for acceptable URL formats.')
    parser.add_option('--server-type',
                      dest='server_type',
                      help='"appengine": The server is AppEngine. '
                           '"local": The server is a local dev_appserver. '
                           'It is guessed automatically when omitted.')
    parser.add_option('--gql-query',
                      dest='gql_query',
                      help='GQL query in the format "select * from ...". It '
                           'deletes all entities matching this query.')
    parser.add_option('--batch-size',
                      dest='batch_size',
                      type='int',
                      default=1000,
                      help='The number of entities in a single deletion batch. '
                      'It shouldn\'t be too large to avoid timeout.')
    parser.add_option('--mode',
                      dest='mode',
                      type='choice',
                      choices=['preview', 'delete'],
                      default='preview',
                      help='"preview": Shows sample entities to be deleted '
                           'without actually deleting them. '
                           '"delete": Actually deletes the entities matching '
                           'the query.')
    parser.add_option('--output-attr',
                      dest='output_attr',
                      default='__key__',
                      help='It outputs the attribute with this name of each '
                           'entity in the log. It outputs the entity key by '
                           'default.')
    options, args = parser.parse_args()

    remote_api.connect(options.url, server_type=options.server_type)

    query = db.GqlQuery(options.gql_query)
    while True:
        entities = query.fetch(limit=options.batch_size)
        if not entities: break

        message_prefix = (
                'Deleting' if options.mode == 'delete' else 'Will delete')
        for entity in entities:
            if options.output_attr == '__key__':
                attr_value = str(entity.key().id_or_name())
            else:
                attr_value = getattr(entity, options.output_attr)
            print('%s %s with %s = %r' % (
                    message_prefix,
                    type(entity).kind(),
                    options.output_attr,
                    attr_value))

        if options.mode == 'delete':
            db.delete(entities)
        else:
            break

    if options.mode == 'preview':
        print (
            '\nAbove are %d (or maybe less) sample entities matching the '
            'query. If you rerun the command with --mode=delete, it will '
            'delete ALL entities matching the query, including those not '
            'dumped above.'
            % options.batch_size)


if __name__ == '__main__':
    main()
