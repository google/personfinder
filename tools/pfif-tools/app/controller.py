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

"""Provides a web interface for pfif_tools."""

from StringIO import StringIO

from django.shortcuts import render
from django.views import View

import pfif_validator
import pfif_diff
import utils

class PfifController(View):
  """Provides common functionality to the different PFIF Tools controllers."""

  def get_file(self, file_number=1, return_filename=False):
    """Gets a file that was pasted in, uploaded, or given by a URL.  If multiple
    files are provided, specify the number of the desired file as file_number.
    Returns None if there is no file.  If return_filename is True, returns a
    tuple: (desired_file, filename)."""
    paste_name = 'pfif_xml_' + str(file_number)
    upload_name = 'pfif_xml_file_' + str(file_number)
    url_name = 'pfif_xml_url_' + str(file_number)
    desired_file = None
    filename = None

    if self.request.POST.get(paste_name):
      desired_file = StringIO(self.request.POST[paste_name])
    elif upload_name in self.request.FILES:
      desired_file = StringIO(self.request.FILES[upload_name].read())
      filename = self.request.FILES[upload_name].name
    elif self.request.POST.get(url_name):
      url = self.request.POST[url_name]
      # make a file-like object out of the URL's xml so we can seek on it
      desired_file = StringIO(utils.open_url(url).read())
      filename = url

    if desired_file is not None:
      if return_filename and filename is not None:
        return (desired_file, filename)
      elif return_filename:
        return (desired_file, None)
      else:
        return desired_file
    else:
      if return_filename:
        return (None, None)
      else:
        return None

class DiffController(PfifController):
  """Displays the diff results page."""

  def post(self, request, *args, **kwargs):
    page_ctx = {'page_title': 'PFIF Diff: Results'}
    file_1, filename_1 = self.get_file(1, return_filename=True)
    file_2, filename_2 = self.get_file(2, return_filename=True)
    if file_1 is None or file_2 is None:
      page_ctx['error'] = 'Missing Input File'
      return render(request, 'error.html', page_ctx)
    page_ctx['filenames'] = [
        {'filename': filename_1, 'shorthand_name': 'A'},
        {'filename': filename_2, 'shorthand_name': 'B'},
    ]
    options = self.request.POST.getlist('options')
    ignore_fields = self.request.POST.get(
        'ignore_fields', default='').split()
    messages = pfif_diff.pfif_file_diff(
        file_1, file_2,
        text_is_case_sensitive='text_is_case_sensitive' in options,
        ignore_fields=ignore_fields,
        omit_blank_fields='omit_blank_fields' in options)
    page_ctx['msgs'] = messages
    page_ctx['msgs_by_category'] = (
        utils.MessagesOutput.group_messages_by_category(messages))
    if 'group_messages_by_record' in options:
      page_ctx['group_messages'] = True
      messages = utils.MessagesOutput.truncate(
          messages, utils.MessagesOutput.GROUPED_TRUNCATE_THRESHOLD)
      page_ctx['msg_grouping'] = utils.MessageGroupingById(messages)
    return render(request, 'diff_results.html', page_ctx)

class ValidatorController(PfifController):
  """Displays the validation results page."""

  def post(self, request, *args, **kwargs):
    page_ctx = {'page_title': 'PFIF Validator: Results'}
    xml_file = self.get_file()
    if xml_file is None:
      page_ctx['error'] = 'Missing Input File'
      return render(request, 'error.html', page_ctx)
    validator = pfif_validator.PfifValidator(xml_file)
    messages = validator.run_validations()
    for msg in messages:
      if msg.xml_line_number != None:
        msg.full_xml_line = validator.tree.lines[msg.xml_line_number - 1]
    page_ctx['messages'] = messages
    page_ctx['msgs_by_category'] = (
        utils.MessagesOutput.group_messages_by_category(messages))
    # print_options is a list of all printing options passed in via checkboxes.
    # It will contain 'show_errors' if the user checked that box, for instance.
    # Thus, saying show_errors='show_errors' in print_options will set
    # show_errors to True if the box was checked and false otherwise.
    print_options = self.request.POST.getlist('print_options')
    show_errors = 'show_errors' in print_options
    show_warnings = 'show_warnings' in print_options
    page_ctx['msgs'] = list(filter(
        lambda msg: ((show_errors and msg.is_error) or
                     (show_warnings and not msg.is_error)), messages))
    page_ctx['show_line_numbers'] = 'show_line_numbers' in print_options
    page_ctx['show_record_ids'] = 'show_record_ids' in print_options
    page_ctx['show_xml_tag'] = 'show_xml_tag' in print_options
    page_ctx['show_xml_text'] = 'show_xml_text' in print_options
    page_ctx['show_full_line'] = 'show_full_line' in print_options
    return render(request, 'validate_results.html', page_ctx)
