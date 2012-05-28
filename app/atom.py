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

"""Atom PFIF 1.2 feed generation."""

__author__ = 'kpy@google.com (Ka-Ping Yee)'

import config
import pfif
from const import ROOT_URL
from pfif import format_boolean, format_utc_datetime, xml_escape
from utils import format_utc_timestamp

def write_element(file, tag, contents, indent=''):
    """Writes a single XML element with the given contents, if non-empty."""
    if contents:
        file.write(indent + '<%s>%s</%s>\n' %
                   (tag, xml_escape(contents).encode('utf-8'), tag))

def format_float(value):
    return ('%f' % value).rstrip('0').rstrip('.')

class AtomRepoVersion:
    GPF_NAMESPACE_URI = 'http://schemas.google.com/personfinder/2012'
    GEORSS_NAMESPACE_URI = 'http://www.georss.org/georss'

    def __init__(self, version):
        self.version = version

    def write_fields(self, file, repo_config, indent):
        # Subclasses should implement this method.
        pass

    def write_titles(self, file, tag, languages, per_language_titles, indent):
        if languages and per_language_titles:
            for lang in languages:
                title = per_language_titles.get(lang, '')
                title_xml = '<%s xml:lang="%s">%s</%s>\n' % (
                    tag, lang, xml_escape(title), tag)
                file.write(indent + title_xml.encode('utf-8'))

    def write_entry(self, file, repo, indent):
        repo_config = config.Configuration(repo)
        file.write(indent + '<entry>\n')
        write_element(file, 'id', '%s/%s' % (ROOT_URL, repo),
                      indent + '  ')
        write_element(file, 'published',
                      format_utc_timestamp(repo_config.published_date),
                      indent + '  ')
        write_element(file, 'updated',
                      format_utc_timestamp(repo_config.updated_date),
                      indent + '  ')
        default_language = (repo_config.language_menu_options or [])[:1]
        self.write_titles(file, 'title', default_language,
                          repo_config.repo_titles, indent + '  ')
        file.write(indent + '  <content type="text/xml">\n')
        file.write(indent + '    <gpf:repo>\n')
        self.write_fields(file, repo_config, indent + ' ' * 6)
        file.write(indent + '    </gpf:repo>\n')
        file.write(indent + '  </content>\n')
        file.write(indent + '</entry>\n')

    def write_feed(self, file, repos, url, title, updated):
        file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        file.write('<feed xmlns="http://www.w3.org/2005/Atom"\n')
        file.write('      xmlns:gpf="%s"\n' % self.GPF_NAMESPACE_URI)
        file.write('      xmlns:georss="%s">\n' % self.GEORSS_NAMESPACE_URI)
        indent = '  '
        write_element(file, 'id', url, indent)
        write_element(file, 'title', title, indent)
        write_element(file, 'updated', format_utc_timestamp(updated), indent)
        for repo in repos:
            self.write_entry(file, repo, indent)
        file.write('</feed>\n')


class AtomRepoVersion_1_0(AtomRepoVersion):
    def write_fields(self, file, repo_config, indent):
        self.write_titles(file, 'gpf:title', repo_config.language_menu_options,
                          repo_config.repo_titles, indent)
        write_element(file, 'gpf:read_auth_key_required',
                      format_boolean(repo_config.read_auth_key_required),
                      indent)
        write_element(file, 'gpf:search_auth_key_required',
                      format_boolean(repo_config.search_auth_key_required),
                      indent)
        center = repo_config.map_default_center or [0, 0]
        file.write(indent + '<gpf:location>\n')
        write_element(file, 'georss:point',
                      '%s %s' % (format_float(center[0]),
                                 format_float(center[1])), indent + '  ')
        file.write(indent + '</gpf:location>\n')

REPO_1_0 = AtomRepoVersion_1_0('1.0')


class AtomPfifVersion:
    def __init__(self, pfif_version):
        self.pfif_version = pfif_version

    def write_person_entry(self, file, person, notes, feed_title, indent=''):
        """Writes a PFIF Atom entry, given a person record and a list of its
        note records.  'feed_title' is the title of the containing feed."""
        file.write(indent + '<entry>\n')
        indent += '  '
        self.pfif_version.write_person(file, person, notes, indent)
        write_element(file, 'id', 'pfif:' + person['person_record_id'], indent)
        first_name = person.get('first_name', '')
        last_name = person.get('last_name', '')
        separator = first_name and last_name and ' ' or ''
        title = first_name + separator + last_name
        write_element(file, 'title', title, indent)
        file.write(indent + '<author>\n')
        write_element(file, 'name', person.get('author_name'), indent + '  ')
        write_element(file, 'email', person.get('author_email'), indent + '  ')
        file.write(indent + '</author>\n')
        write_element(file, 'updated', person.get('source_date'), indent)
        file.write(indent + '<source>\n')
        write_element(file, 'title', feed_title, indent + '  ')
        file.write(indent + '</source>\n')
        write_element(file, 'content', title, indent)
        indent = indent[2:]
        file.write(indent + '</entry>\n')

    def write_person_feed(self, file, persons, get_notes_for_person,
                          url, title, subtitle, updated):
        """Takes a list of person records and a function that gets the list
        of note records for each person, and writes a PFIF Atom feed to the
        given file."""
        file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        file.write('<feed xmlns="http://www.w3.org/2005/Atom"\n')
        file.write('      xmlns:pfif="%s">\n' % self.pfif_version.ns)
        write_element(file, 'id', url, '  ')
        write_element(file, 'title', title, '  ')
        write_element(file, 'subtitle', subtitle, '  ')
        write_element(file, 'updated', format_utc_datetime(updated), '  ')
        file.write('  <link rel="self">%s</link>\n' % xml_escape(url))
        for person in persons:
            self.write_person_entry(
                file, person, get_notes_for_person(person), title, '  ')
        file.write('</feed>\n')

    def write_note_entry(self, file, note, indent=''):
        """Writes a PFIF Atom entry, given a note record."""
        file.write(indent + '<entry>\n')
        indent += '  '
        self.pfif_version.write_note(file, note, indent)
        write_element(file, 'id', 'pfif:%s' % note['note_record_id'], indent)
        write_element(file, 'title', note.get('text', '')[:140], indent)
        file.write(indent + '<author>\n')
        write_element(file, 'name', note.get('author_name'), indent + '  ')
        write_element(file, 'email', note.get('author_email'), indent + '  ')
        file.write(indent + '</author>\n')
        write_element(file, 'updated', note.get('entry_date'), indent)
        write_element(file, 'content', note.get('text'), indent)
        indent = indent[2:]
        file.write(indent + '</entry>\n')

    def write_note_feed(self, file, notes, url, title, subtitle, updated):
        """Takes a list of notes and writes a PFIF Atom feed to a file."""
        file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        file.write('<feed xmlns="http://www.w3.org/2005/Atom"\n')
        file.write('      xmlns:pfif="%s">\n' % self.pfif_version.ns)
        write_element(file, 'id', url, '  ')
        write_element(file, 'title', title, '  ')
        write_element(file, 'subtitle', subtitle, '  ')
        write_element(file, 'updated', format_utc_datetime(updated), '  ')
        file.write('  <link rel="self">%s</link>\n' % xml_escape(url))
        for note in notes:
            self.write_note_entry(file, note, '  ')
        file.write('</feed>\n')

ATOM_PFIF_1_2 = AtomPfifVersion(pfif.PFIF_1_2)
ATOM_PFIF_1_3 = AtomPfifVersion(pfif.PFIF_1_3)

ATOM_PFIF_VERSIONS = {
    '1.2': ATOM_PFIF_1_2,
    '1.3': ATOM_PFIF_1_3
}
