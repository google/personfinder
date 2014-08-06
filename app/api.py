#!/usr/bin/python2.7
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

"""Basic API for reading/writing small numbers of records."""

__author__ = 'kpy@google.com (Ka-Ping Yee)'

import calendar
import csv
import logging
import re
import StringIO
import xml.dom.minidom

import django.utils.html
from google.appengine import runtime

import external_search
import importer
import indexing
import model
import pfif
import simplejson
import subscribe
import utils
from model import Person, Note, ApiActionLog
from text_query import TextQuery
from utils import Struct


HARD_MAX_RESULTS = 200  # Clients can ask for more, but won't get more.


class InputFileError(Exception):
    pass


def get_requested_formats(path):
    """Returns a list of requested formats.
    The possible values are 'persons' and 'notes'."""
    format = path.split('/')[-1]
    if format in ['persons', 'notes']:
        return [format]
    return ['persons', 'notes']


def complete_record_ids(record, domain):
    """Ensures that a record's record_id fields are prefixed with a domain."""
    def complete(record, field):
        id = record.get(field)
        if id and '/' not in id:
            record[field] = '%s/%s' % (domain, id)
    complete(record, 'person_record_id')
    complete(record, 'note_record_id')
    return record


def get_tag_params(handler):
    """Return HTML tag parameters used in import.html."""
    return {
        'begin_notes_template_link':
            '<a href="%s/notes-template.xlsx">' %
                django.utils.html.escape(handler.env.global_url),
        'end_notes_template_link':
            '</a>',
        'begin_sample_anchor_tag':
            '<a href="%s/sample-import.csv" target="_blank">' %
                django.utils.html.escape(handler.env.global_url),
        'end_sample_anchor_tag':
            '</a>',
        'begin_document_anchor_tag':
            '<a href='
            '"https://code.google.com/p/googlepersonfinder/wiki/ImportCSV" '
            'target="_blank">',
        'end_document_anchor_tag':
            '</a>',
    }


def generate_note_record_ids(records):
    for record in records:
        if not record.get('note_record_id', '').strip():
            record['note_record_id'] = str(model.UniqueId.create_id())
        yield record


def convert_time(text, offset):
    """Converts a textual date and time into an RFC 3339 UTC timestamp."""
    if utils.DATETIME_RE.match(text.strip()):  # don't apply offset
        return text
    match = re.search(r'(\d\d\d\d)[/-](\d+)[/-](\d+) *(\d+):(\d+)', text)
    if match:
        y, l, d, h, m = map(int, match.groups())
        timestamp = calendar.timegm((y, l, d, h, m, 0)) - offset*3600
        return utils.format_utc_timestamp(timestamp)
    return text  # keep the original text so it shows up in the error message


def convert_time_fields(rows, default_offset=0):
    """Filters CSV rows, converting time fields to RFC 3339 UTC times.

    The first row that contains "person_record_id" is assumed to be the header
    row containing field names.  Preceding rows are treated as a preamble.

    If the text "time_zone_offset" is found in the preamble section, the cell
    immediately below it is treated as a time zone offset from UTC in hours.
    Otherwise default_offset is used as the time zone offset.

    Rows below the header row are returned as dictionaries (as csv.DictReader
    would), except that any "*_date" fields are parsed as local times,
    converted to UTC according to the specified offset, and reformatted
    as RFC 3339 UTC times.
    """
    field_names = []
    time_fields = []
    setting_names = []
    settings = {}
    offset = default_offset

    for row in rows:
        if field_names:
            record = dict(zip(field_names, row))
            for key in time_fields:
                record[key] = convert_time(record[key], offset)
            yield record

        elif 'person_record_id' in row:
            field_names = [name.lower().strip() for name in row]
            time_fields = [name for name in row if name.endswith('_date')]
            if 'time_zone_offset' in settings:
                try:
                    offset = float(settings['time_zone_offset'])
                except ValueError:
                    raise InputFileError('invalid time_zone_offset value')

        else:
            settings.update(dict(zip(setting_names, row)))
            setting_names = [name.lower().strip() for name in row]


class Import(utils.BaseHandler):
    https_required = True

    def get(self):
        self.render('import.html',
                    formats=get_requested_formats(self.env.path),
                    params=self.params,
                    **get_tag_params(self))

    def post(self):
        if not (self.auth and self.auth.domain_write_permission):
            # TODO(ryok): i18n
            self.error(403, message='Missing or invalid authorization key.')
            return

        content = self.request.get('content')
        if not content:
            self.error(400, message='Please specify at least one CSV file.')
            return

        try:
            lines = content.splitlines()  # handles \r, \n, or \r\n
            if self.request.get('format') == 'notes':
                self.import_notes(lines)
            else:
                self.import_persons(lines)
        except InputFileError, e:
            self.error(400, message='Problem in the uploaded file: %s' % e)
        except runtime.DeadlineExceededError, e:
            self.error(400, message=
                'Sorry, the uploaded file is too large. Try splitting it into '
                'smaller files (keeping the header rows in each file) and '
                'uploading each part separately.')

    def import_notes(self, lines):
        source_domain = self.auth.domain_write_permission
        records = importer.utf8_decoder(generate_note_record_ids(
            convert_time_fields(csv.reader(lines))))
        try:
            records = [complete_record_ids(r, source_domain) for r in records]
        except csv.Error, e:
            self.error(400, message=
                'The CSV file is formatted incorrectly. (%s)' % e)
            return

        notes_written, notes_skipped, notes_total = importer.import_records(
            self.repo, source_domain, importer.create_note, records,
            believed_dead_permission=self.auth.believed_dead_permission,
            omit_duplicate_notes=True)

        utils.log_api_action(self, ApiActionLog.WRITE,
                             0, notes_written, 0, len(notes_skipped))

        self.render('import.html',
                    formats=get_requested_formats(self.env.path),
                    params=self.params,
                    stats=[
                        Struct(type='Note',
                               written=notes_written,
                               skipped=notes_skipped,
                               total=notes_total)],
                    **get_tag_params(self))

    def import_persons(self, lines):
        # TODO(ryok): support non-UTF8 encodings.

        source_domain = self.auth.domain_write_permission
        records = importer.utf8_decoder(convert_time_fields(csv.reader(lines)))
        try:
            records = [complete_record_ids(r, source_domain) for r in records]
        except csv.Error, e:
            self.error(400, message=
                'The CSV file is formatted incorrectly. (%s)' % e)
            return

        is_not_empty = lambda x: (x or '').strip()
        persons = [r for r in records if is_not_empty(r.get('full_name'))]
        notes = [r for r in records if is_not_empty(r.get('note_record_id'))]

        people_written, people_skipped, people_total = importer.import_records(
            self.repo, source_domain, importer.create_person, persons)
        notes_written, notes_skipped, notes_total = importer.import_records(
            self.repo, source_domain, importer.create_note, notes,
            believed_dead_permission=self.auth.believed_dead_permission)

        utils.log_api_action(self, ApiActionLog.WRITE,
                             people_written, notes_written,
                             len(people_skipped), len(notes_skipped))

        self.render('import.html',
                    formats=get_requested_formats(self.env.path),
                    params=self.params,
                    stats=[
                        Struct(type='Person',
                               written=people_written,
                               skipped=people_skipped,
                               total=people_total),
                        Struct(type='Note',
                               written=notes_written,
                               skipped=notes_skipped,
                               total=notes_total)],
                    **get_tag_params(self))


class Read(utils.BaseHandler):
    https_required = True

    def get(self):
        if self.config.read_auth_key_required and not (
            self.auth and self.auth.read_permission):
            self.info(
                403,
                message='Missing or invalid authorization key',
                style='plain')
            return

        pfif_version = self.params.version

        # Note that self.request.get can handle multiple IDs at once; we
        # can consider adding support for multiple records later.
        record_id = self.request.get('id')
        if not record_id:
            self.info(400, message='Missing id parameter', style='plain')
            return

        person = model.Person.get(
            self.repo, record_id, filter_expired=False)
        if not person:
            self.info(
                400,
                message='No person record with ID %s' % record_id,
                style='plain')
            return
        notes = model.Note.get_by_person_record_id(self.repo, record_id)
        notes = [note for note in notes if not note.hidden]

        self.response.headers['Content-Type'] = 'application/xml'
        records = [pfif_version.person_to_dict(person, person.is_expired)]
        note_records = map(pfif_version.note_to_dict, notes)
        utils.optionally_filter_sensitive_fields(records, self.auth)
        utils.optionally_filter_sensitive_fields(note_records, self.auth)
        pfif_version.write_file(
            self.response.out, records, lambda p: note_records)
        utils.log_api_action(
            self, ApiActionLog.READ, len(records), len(notes))


class Write(utils.BaseHandler):
    https_required = True

    def post(self):
        if not (self.auth and self.auth.domain_write_permission):
            self.info(
                403,
                message='Missing or invalid authorization key',
                style='plain')
            return

        source_domain = self.auth.domain_write_permission
        try:
            person_records, note_records = \
                pfif.parse_file(self.request.body_file)
        except Exception, e:
            self.info(400, message='Invalid XML: %s' % e, style='plain')
            return

        mark_notes_reviewed = bool(self.auth.mark_notes_reviewed)
        believed_dead_permission = bool(
            self.auth.believed_dead_permission)

        self.response.headers['Content-Type'] = 'application/xml'
        self.write('<?xml version="1.0"?>\n')
        self.write('<status:status>\n')

        create_person = importer.create_person
        num_people_written, people_skipped, total = importer.import_records(
            self.repo, source_domain, create_person, person_records)
        self.write_status(
            'person', num_people_written, people_skipped, total, 
            'person_record_id')

        create_note = importer.create_note
        num_notes_written, notes_skipped, total = importer.import_records(
            self.repo, source_domain, create_note, note_records,
            mark_notes_reviewed, believed_dead_permission, self)

        self.write_status(
            'note', num_notes_written, notes_skipped, total, 'note_record_id')

        self.write('</status:status>\n')
        utils.log_api_action(self, ApiActionLog.WRITE,          
                             num_people_written, num_notes_written,  
                             len(people_skipped), len(notes_skipped))


    def write_status(self, type, written, skipped, total, id_field):
        """Emit status information about the results of an attempted write."""
        skipped_records = []
        for error, record in skipped:
            skipped_records.append(
                '      <pfif:%s>%s</pfif:%s>\n' %
                (id_field, record.get(id_field, ''), id_field))
            skipped_records.append(
                '      <status:error>%s</status:error>\n' % error)

        self.write('''
  <status:write>
    <status:record_type>pfif:%s</status:record_type>
    <status:parsed>%d</status:parsed>
    <status:written>%d</status:written>
    <status:skipped>
%s
    </status:skipped>
  </status:write>
''' % (type, total, written, ''.join(skipped_records).rstrip()))


class Search(utils.BaseHandler):
    https_required = False

    def get(self):
        if self.config.search_auth_key_required and not (
            self.auth and self.auth.search_permission):
            self.info(
                403,
                message='Missing or invalid authorization key',
                style='plain')
            return

        pfif_version = self.params.version

        # Retrieve parameters and do some sanity checks on them.
        record_id = self.request.get('id')
        query_string = self.request.get('q')
        max_results = min(self.params.max_results or 100, HARD_MAX_RESULTS)

        results = []
        if record_id:
            # Search by record ID (always returns just 1 result or nothing).
            person = model.Person.get(self.repo, record_id)
            if person:
                results = [person]
        elif query_string:
            # Search by query words.
            query = TextQuery(query_string)
            if self.config.external_search_backends:
                results = external_search.search(self.repo, query, max_results,
                    self.config.external_search_backends)
            # External search backends are not always complete. Fall back to
            # the original search when they fail or return no results.
            if not results:
                results = indexing.search(self.repo, query, max_results)
        else:
            self.info(
                400,
                message='Neither id nor q parameter specified',
                style='plain')

        records = [pfif_version.person_to_dict(result) for result in results]
        utils.optionally_filter_sensitive_fields(records, self.auth)

        # Define the function to retrieve notes for a person.
        def get_notes_for_person(person):
            notes = model.Note.get_by_person_record_id(
                self.repo, person['person_record_id'])
            notes = [note for note in notes if not note.hidden]
            records = map(pfif_version.note_to_dict, notes)
            utils.optionally_filter_sensitive_fields(records, self.auth)
            return records

        self.response.headers['Content-Type'] = 'application/xml'
        pfif_version.write_file(
            self.response.out, records, get_notes_for_person)
        utils.log_api_action(self, ApiActionLog.SEARCH, len(records))


class Subscribe(utils.BaseHandler):
    https_required = True

    def post(self):
        if not (self.auth and self.auth.subscribe_permission):
            return self.error(403, 'Missing or invalid authorization key')

        if not subscribe.is_email_valid(self.params.subscribe_email):
            return self.error(400, 'Invalid email address')

        person = model.Person.get(self.repo, self.params.id)
        if not person:
            return self.error(400, 'Invalid person_record_id')

        subscription = subscribe.subscribe_to(self, self.repo, person,
                                              self.params.subscribe_email,
                                              self.env.lang)
        utils.log_api_action(self, ApiActionLog.SUBSCRIBE)
        if not subscription:
            return self.info(200, 'Already subscribed')
        return self.info(200, 'Successfully subscribed')


class Unsubscribe(utils.BaseHandler):
    https_required = True

    def post(self):
        if not (self.auth and self.auth.subscribe_permission):
            return self.error(403, 'Missing or invalid authorization key')

        subscription = model.Subscription.get(self.repo, self.params.id,
                                              self.params.subscribe_email)
        self.response.set_status(200)
        utils.log_api_action(self, ApiActionLog.UNSUBSCRIBE)
        if subscription:
            subscription.delete()
            return self.info(200, 'Successfully unsubscribed')
        return self.info(200, 'Not subscribed')


def fetch_all(query):
    results = []
    batch = query.fetch(500)
    while batch:
        results += batch
        batch = query.with_cursor(query.cursor()).fetch(500)
    return results


class Stats(utils.BaseHandler):
    def get(self):
        if not (self.auth and self.auth.stats_permission):
            self.info(
                403,
                message='Missing or invalid authorization key',
                style='plain')
            return

        person_counts = model.Counter.get_all_counts(self.repo, 'person')
        note_counts = model.Counter.get_all_counts(self.repo, 'note')

        # unreviewed
        note_counts['hidden=FALSE,reviewed=FALSE'] = len(fetch_all(
            model.Note.all(keys_only=True
            ).filter('repo =', self.repo
            ).filter('reviewed =', False
            ).filter('hidden =', False
            ).order('-entry_date')))
        # accepted
        note_counts['hidden=FALSE,reviewed=TRUE'] = len(fetch_all(
            model.Note.all(keys_only=True
            ).filter('repo =', self.repo
            ).filter('reviewed =', True
            ).filter('hidden =', False
            ).order('-entry_date')))
        # flagged
        note_counts['hidden=TRUE'] = len(fetch_all(
            model.Note.all(keys_only=True
            ).filter('repo =', self.repo
            ).filter('hidden =', True
            ).order('-entry_date')))

        self.response.headers['Content-Type'] = 'application/json'
        self.write(simplejson.dumps({'person': person_counts,
                                     'note': note_counts}))


class HandleSMS(utils.BaseHandler):
    https_required = True
    repo_required = False

    MAX_RESULTS = 3

    def post(self):
        if not (self.auth and self.auth.search_permission):
            self.info(
                403,
                message=
                    '"key" URL parameter is either missing, invalid or '
                    'lacks required permissions. The key\'s repo must be "*" '
                    'and search_permission must be True.',
                style='plain')
            return

        body = self.request.body_file.read()
        doc = xml.dom.minidom.parseString(body)
        message_text = self.get_element_text(doc, 'message_text')
        receiver_phone_number = self.get_element_text(
            doc, 'receiver_phone_number')

        if message_text is None:
            self.info(
                400,
                message='message_text element is required.',
                style='plain')
            return
        if receiver_phone_number is None:
            self.info(
                400,
                message='receiver_phone_number element is required.',
                style='plain')
            return

        repo = (
            self.config.sms_number_to_repo and
            self.config.sms_number_to_repo.get(receiver_phone_number))
        if not repo:
            self.info(
                400,
                message=
                    'The given receiver_phone_number is not found in '
                    'sms_number_to_repo config.',
                style='plain')
            return

        responses = []
        m = re.search(r'^search\s+(.+)$', message_text.strip(), re.I)
        if m:
            query_string = m.group(1).strip()
            query = TextQuery(query_string)
            persons = indexing.search(repo, query, HandleSMS.MAX_RESULTS)
            if persons:
                for person in persons:
                    responses.append(self.render_person(person))
            else:
                responses.append('No results found for: %s' % query_string)
            responses.append(
                'More at: http://g.co/pf/%s' % repo)
            responses.append(
                'All data entered in Person Finder is available to the public '
                'and usable by anyone. Google does not review or verify the '
                'accuracy of this data http://goo.gl/UCAXa')
        else:
            responses.append('Usage: Search John')

        self.response.headers['Content-Type'] = 'application/xml'
        self.write(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<response>\n'
            '  <message_text>%s</message_text>\n'
            '</response>\n'
            % django.utils.html.escape(' ## '.join(responses)))

    def render_person(self, person):
        fields = []
        fields.append(person.full_name)
        if person.latest_status:
            # The result of utils.get_person_status_text() may be a Django's
            # proxy object for lazy translation. Use unicode() to convert it
            # into a unicode object. We must not specify an encoding for
            # unicode() in this case.
            fields.append(unicode(
                utils.get_person_status_text(person)))
        if person.sex: fields.append(person.sex)
        if person.age: fields.append(person.age)
        if person.home_city or person.home_state:
            fields.append(
                'From: ' +
                ' '.join(filter(None, [person.home_city, person.home_state])))
        return ' / '.join(fields)

    def get_element_text(self, doc, tag_name):
        elems = doc.getElementsByTagName(tag_name)
        if elems:
            text = u''
            for node in elems[0].childNodes:
                if node.nodeType == node.TEXT_NODE:
                    text += node.data
            return text.encode('utf-8')
        else:
            return None
