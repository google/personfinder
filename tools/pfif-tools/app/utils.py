#!/usr/bin/env python
# Copyright 2011 Google Inc.
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

"""Utilities for the PFIF Validator"""

import re
from datetime import datetime
import xml.etree.ElementTree as ET
import urllib
import cgi

# XML Parsing Utilities

def extract_tag(etree_tag):
  """An etree tag comes in the form: {namespace}tag.  This returns the tag"""
  match = re.match(r'(?:\{.+\})?(.+)', etree_tag)
  if not match:
    return ""
  return match.group(1)

# Dependency Injection for Time -- from PersonFinder
_utcnow_for_test = None # pylint: disable=c0103

def set_utcnow_for_test(now):
  """Set current time for debug purposes."""
  global _utcnow_for_test # pylint: disable=w0603
  _utcnow_for_test = now

# Dependency injection for files
_file_for_test = None # pylint: disable=c0103

def set_file_for_test(file_for_test):
  """Set current file or url for debugging purposes."""
  global _file_for_test # pylint: disable=w0603
  _file_for_test = file_for_test

def open_file(filename, mode='r'):
  """Opens the file or returns a debug value if set."""
  return _file_for_test or open(filename, mode)

# TODO(samking): do incremental URL reading to support massive files
def open_url(url):
  """Opens the url or returns a debug value if set."""
  return _file_for_test or urllib.urlopen(url)

def get_utcnow():
  """Return current time in utc, or debug value if set."""
  return _utcnow_for_test or datetime.utcnow()

class FileWithLines:
  """A file that keeps track of its line number.  From
  http://bytes.com/topic/python/answers/535191-elementtree-line-numbers-iterparse
  """

  def __init__(self, source):
    self.source = source
    self.line_number = 0

  def read(self, num_bytes): # pylint: disable=W0613
    """Wrapper around file.readLine that keeps track of line number"""
    self.line_number += 1
    return self.source.readline()

# Doesn't inherit from ET.ElementTree to avoid messing with the
# ET.ElementTree.parse factory method
class PfifXmlTree():
  """An XML tree with PFIF-XML-specific helper functions."""

  def __init__(self, xml_file):
    self.namespace = None
    self.version = None
    self.tree = None
    self.line_numbers = {}
    self.lines = xml_file.readlines()
    xml_file.seek(0)
    self.initialize_tree(xml_file)
    self.initialize_pfif_version()


  def initialize_tree(self, xml_file):
    """Reads in the XML tree from the XML file.  If the XML file is invalid,
    the XML library will raise an exception."""
    file_with_lines = FileWithLines(xml_file)
    tree_parser = iter(ET.iterparse(file_with_lines, events=['start']))
    event, root = tree_parser.next() # pylint: disable=W0612
    self.line_numbers[root] = file_with_lines.line_number

    for event, elem in tree_parser:
      self.line_numbers[elem] = file_with_lines.line_number
    self.tree = ET.ElementTree(root)

  def initialize_pfif_version(self):
    """Initializes the namespace and version.  Raises an exception of the XML
    root does not specify a namespace or tag, if the tag isn't pfif, or if the
    version isn't supported."""
    root = self.tree.getroot()
    tag = root.tag
    # xml.etree.Element.tag is formatted like: {namespace}tag
    match = re.match(r'\{(.+)\}(.+)', tag)
    assert match, 'This XML root node does not specify a namespace and tag'
    self.namespace = match.group(1)
    tag = match.group(2)
    assert tag == 'pfif', 'The root node must be pfif'

    # the correct pfif url is like: http://zesty.ca/pfif/VERSION where VERSION
    # is 1.1, 1.2, or 1.3
    match = re.match(r'http://zesty\.ca/pfif/(\d\.\d)', self.namespace)
    assert match, ('The XML namespace specified is not correct.  It should be '
                   'in the following format: http://zesty.ca/pfif/VERSION')
    self.version = float(match.group(1))
    assert (self.version >= 1.1 and self.version <= 1.3), (
           'This validator only supports versions 1.1-1.3.')

  def getroot(self):
    """wrapper for ET.ElementTree.getroot."""
    return self.tree.getroot()

  def add_namespace_to_tag(self, tag):
    """turns a local tag into a fully qualified tag by adding a namespace """
    return '{' + self.namespace + '}' + tag

  def get_all_persons(self):
    """returns a list of all persons in the tree"""
    return self.tree.findall(self.add_namespace_to_tag('person'))

  def get_child_notes(self):
    """returns a list of all notes that are subnodes of persons"""
    notes = []
    for person in self.get_all_persons():
      notes.extend(person.findall(self.add_namespace_to_tag('note')))
    return notes

  def get_top_level_notes(self):
    """returns a list of all notes that are subnodes of the root node"""
    return self.tree.findall(self.add_namespace_to_tag('note'))

  def get_all_notes(self):
    """returns a list of all notes in the tree"""
    notes = self.get_top_level_notes()
    notes.extend(self.get_child_notes())
    return notes

  def get_field_text(self, parent, child_tag):
    """Returns the text associated with the child node of parent.  Returns none
    if parent doesn't have that child or if the child doesn't have any text"""
    child = parent.find(self.add_namespace_to_tag(child_tag))
    if child != None:
      return child.text
    return None

class Message: # pylint: disable=R0902
  """A container for information about an error or warning message"""

  def __init__(self, category, extra_data=None, is_error=True,
               xml_line_number=None, xml_tag=None, xml_text=None,
               person_record_id=None, note_record_id=None):
    self.category = category
    self.extra_data = extra_data
    self.is_error = is_error
    self.xml_line_number = xml_line_number
    self.xml_text = xml_text
    self.xml_tag = xml_tag
    self.person_record_id = person_record_id
    self.note_record_id  = note_record_id

  def __eq__(self, other):
    return self.__dict__ == other.__dict__

class Categories: # pylint: disable=W0232
  """Constants representing message categories."""

  ADDED_RECORD  = 'B has extra records'
  DELETED_RECORD = 'B is missing records'
  ADDED_FIELD = 'B has extra fields'
  DELETED_FIELD = 'B is missing fields'
  CHANGED_FIELD = 'Values changed'


class MessagesOutput:
  """A container that allows for outputting either a plain string or HTML
  easily"""

  # If truncation is on, only this many messages will be allowed per category
  TRUNCATE_THRESHOLD = 100

  # When using grouped output (messages_to_str_by_id), it's more compact and
  # less in need of truncation.
  GROUPED_TRUNCATE_THRESHOLD = 400

  def __init__(self, is_html, html_class='all_messages'):
    self.is_html = is_html
    self.output = []
    if is_html:
      self.output.append('<div class="' + html_class + '">')

  def get_output(self):
    """Turns the stored data into a string.  Call at most once per instance of
    MessagesOutput."""
    if self.is_html:
      # closes all_messages div
      self.output.append('</div>')
    return ''.join(self.output)

  def start_new_message(self):
    """Call once at the start of each message before calling
    make_message_part"""
    if self.is_html:
      self.output.append('<div class="message">')

  def end_new_message(self):
    """Call once at the end of each message after all calls to
    make_message_part"""
    if self.is_html:
      # clases message div
      self.output.append('</div>')
    self.output.append('\n')

  def make_message_part(self, text, html_class, inline, data=None):
    """Call once for each different part of the message (ie, the main text, the
    line number).  text is the body of the message.  html_class is the class of
    the span or div that will contain the text.  inline should be True if spans
    are desired and False if divs are desired.  data will be enclosed in a
    message_data span regardless of whethether the message part as a whole is
    inline or not."""
    if self.is_html:
      if inline:
        tag_type = 'span'
      else:
        tag_type = 'div'
      self.output.append('<' + tag_type + ' class="' + html_class + '">')
      self.output.append(cgi.escape(text))
      if data != None:
        self.output.append('<span class="message_data">' + data + '</span>')
      self.output.append('</' + tag_type + '>')
    else:
      if not inline:
        self.output.append('\n')
      self.output.append(text)
      if data != None:
        self.output.append(data)

  def make_message_part_division(self, text, html_class, data=None):
    """Wrapper for make_message_part that is not inline."""
    self.make_message_part(text, html_class, inline=False, data=data)

  def make_message_part_inline(self, text, html_class, data=None):
    """Wrapper for make_message_part that is inline."""
    self.make_message_part(text, html_class, inline=True, data=data)

  def start_table(self, headers):
    """Adds a table header to the output.  Call before using make_table_row."""
    if self.is_html:
      self.output.append('<table>')
    self.make_table_row(headers, row_tag='th')

  def end_table(self):
    """Closes a table header.  Call after using make_table_row."""
    if self.is_html:
      self.output.append('</table>')

  def make_table_row(self, elements, row_tag='td'):
    """Makes a table row where every element in elements is in the row."""
    if self.is_html:
      self.output.append('<tr>')
    for element in elements:
      if self.is_html:
        self.output.append('<' + row_tag + '>' + element + '</' + row_tag + '>')
      else:
        self.output.append(element + '\t')
    if self.is_html:
      self.output.append('</tr>')
    else:
      self.output.append('\n')

  # TODO(samking): add ability to turn off truncate in controller and main
  @staticmethod
  def truncate(messages, truncation_threshold):
    """Only allows truncation_threshold messages per category.  Adds one message
    for each category that is truncated."""
    messages_by_category = MessagesOutput.group_messages_by_category(messages)
    truncated_messages = []
    for category, message_list in messages_by_category.items():
      # add at most truncation_threshold messages to truncated_messages
      truncated_messages.extend(message_list[:truncation_threshold])
      # add a message saying that truncation happened
      if len(message_list) > truncation_threshold:
        truncated_messages.append(Message(
            'You had too many messages, so some were truncated.',
            extra_data='You had ' + str(len(message_list)) + ' messages in the '
            'following category: ' + category + '.'))
    return truncated_messages

  @staticmethod
  def group_messages_by_record(messages):
    """Returns a dict from record_id to a list of messages with that id.
    person_record_id and note_record_id are treated the same."""
    grouped_messages = {}
    for message in messages:
      record_id = (message.person_record_id or message.note_record_id or
                   'None Specified')
      record_message_list = grouped_messages.setdefault(record_id, [])
      record_message_list.append(message)
    return grouped_messages

  @staticmethod
  def group_messages_by_category(messages):
    """Returns a dict from category to a list of messages with that category."""
    grouped_messages = {}
    for message in messages:
      grouped_messages.setdefault(message.category, []).append(message)
    return grouped_messages

  @staticmethod
  def get_field_from_messages(messages, field):
    """Returns a list of the value of field for each message."""
    if field == 'record_id':
      fields = []
      for message in messages:
        fields.append(message.note_record_id or message.person_record_id)
      return fields
    else:
      # TODO(samking): is there a better way to dynamically access a field of an
      # object than using the __dict__ object?
      return [message.__dict__[field] for message in messages]

  @staticmethod
  def generate_message_summary(messages, is_html):
    """Returns a string with a summary of the categories of each message."""
    output = MessagesOutput(is_html, html_class="summary")
    messages_by_category = MessagesOutput.group_messages_by_category(messages)
    output.start_table(['Category', 'Number of Messages'])
    for category, messages_list in messages_by_category.items():
      output.make_table_row([category, str(len(messages_list))])
    output.end_table()
    return output.get_output()

  @staticmethod
  def messages_to_str_by_id(messages, is_html=False, truncate=True):
    """Returns a string containing all messages grouped together by record.
    Only works on diff messages."""
    if truncate:
      messages = MessagesOutput.truncate(
          messages, MessagesOutput.GROUPED_TRUNCATE_THRESHOLD)
    output = MessagesOutput(is_html)
    list_records_categories = [Categories.ADDED_RECORD,
                               Categories.DELETED_RECORD]
    list_fields_categories =  [Categories.ADDED_FIELD,
                               Categories.DELETED_FIELD,
                               Categories.CHANGED_FIELD]
    messages_by_category = MessagesOutput.group_messages_by_category(messages)

    # Output Records Added and Deleted
    for category in list_records_categories:
      changed_records_messages = messages_by_category.get(category)
      if changed_records_messages:
        output.start_new_message()
        output.make_message_part_division(
            category + ': ' + str(len(changed_records_messages)) + ' messages.',
            'grouped_record_header')
        record_ids_changed = MessagesOutput.get_field_from_messages(
            changed_records_messages, 'record_id')
        output.make_message_part_division(
            'Record IDs: ', 'grouped_record_list',
            data=', '.join(record_ids_changed))
        output.end_new_message()

    # Extract Messages with Changed Records
    messages_by_record = []
    for category in list_fields_categories:
      messages_by_record.extend(messages_by_category.get(category, []))
    messages_by_record = MessagesOutput.group_messages_by_record(
        messages_by_record)

    # Output Records Changed
    for record, record_list in messages_by_record.items():
      output.start_new_message()
      output.make_message_part_division(
          str(len(record_list)) + ' messages for record: ' + record,
          'grouped_record_header')
      record_messages_by_category = MessagesOutput.group_messages_by_category(
          record_list)
      for category in list_fields_categories:
        tag_list = MessagesOutput.get_field_from_messages(
            record_messages_by_category.get(category, []), 'xml_tag')
        if tag_list:
          output.make_message_part_division(
              category + ': ', 'grouped_record_list', data=', '.join(tag_list))
      output.end_new_message()

    return output.get_output()

  @staticmethod
  # pylint: disable=R0912
  def messages_to_str(messages, show_error_type=True, show_errors=True,
                      show_warnings=True, show_line_numbers=True,
                      show_full_line=True, show_record_ids=True,
                      show_xml_tag=True, show_xml_text=True, is_html=False,
                      xml_lines=None, truncate=True):
    # pylint: enable=R0912
    """Returns a string containing all messages formatted per the options."""
    if truncate:
      messages = MessagesOutput.truncate(
          messages, MessagesOutput.TRUNCATE_THRESHOLD)
    output = MessagesOutput(is_html)
    for message in messages:
      if (message.is_error and show_errors) or (
          not message.is_error and show_warnings):
        output.start_new_message()
        if show_error_type and message.is_error:
          output.make_message_part_inline('ERROR ', 'message_type')
        if show_error_type and not message.is_error:
          output.make_message_part_inline('WARNING ', 'message_type')
        if (show_line_numbers and message.xml_line_number != None):
          output.make_message_part_inline('Line ' + str(message.xml_line_number)
                                          + ': ', 'message_line_number')
        if message.extra_data == None:
          output.make_message_part_inline(message.category,
                                          'message_category')
        else:
          output.make_message_part_inline(message.category, 'message_category',
                                          data=': ' + message.extra_data)
        if show_record_ids:
          if message.person_record_id != None:
            output.make_message_part_division(
                'The relevant person_record_id is: ',
                'message_person_record_id', data=message.person_record_id)
          if message.note_record_id != None:
            output.make_message_part_division(
                'The relevant note_record_id is: ',
                'message_note_record_id', data=message.note_record_id)
        if show_xml_tag and message.xml_tag:
          output.make_message_part_division(
              'The tag of the relevant PFIF XML node: ', 'message_xml_tag',
              data=message.xml_tag)
        if show_xml_text and message.xml_text:
          output.make_message_part_division(
              'The text of the relevant PFIF XML node: ', 'message_xml_text',
              data=message.xml_text)
        if (show_full_line and message.xml_line_number != None):
          output.make_message_part_division(
              xml_lines[message.xml_line_number - 1], 'message_xml_full_line')
        output.end_new_message()
    return output.get_output()
