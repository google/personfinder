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

from datetime import datetime
from model import *
from utils import *
from google.appengine.api import images
from google.appengine.runtime.apiproxy_errors import RequestTooLargeError
import indexing
import prefix

MAX_IMAGE_DIMENSION = 300

def person_page_url(prefix, person):
  return '%s/view?%s' % (prefix, urlencode({'id': person.person_record_id}))

def validate_date(string):
  """Parses a date in YYYY-MM-DD format.  This is a special case for manual
  entry of the source_date in the creation form.  Unlike the validators in
  utils.py, this will throw an exception if the input is badly formatted."""
  year, month, day = map(int, string.strip().split('-'))
  return datetime(year, month, day)


class Create(Handler):
  def get(self):
    self.params.create_mode = True
    self.render('templates/create.html', params=self.params,
                onload_function="view_page_loaded()")

  def post(self):
    if config.USE_FAMILY_NAME:
      if not (self.params.first_name and self.params.last_name):
        # makemessages can't handle translated strings on multiple lines. :(
        return self.error(400, _('The Given name and Family name are both required.  Please go back and try again.'))
    else:
      if not self.params.first_name:
        # makemessages can't handle translated strings on multiple lines. :(
        return self.error(400, _('Name is required.  Please go back and try again.'))
    if not self.params.author_name:
      if self.params.clone:
        return self.error(400, _('The Original author\'s name is required.  Please go back and try again.'))
      else:
        return self.error(400, _('Your name is required in the "Source" section.  Please go back and try again.'))

    if self.params.add_note:
      if not self.params.text:
        return self.error(400, _('Message is required. Please go back and try again.'))
      if self.params.status == 'is_note_author' and not self.params.found:
        return self.error(400, _('Please check that you have been in contact with the person after the earthquake, or change the "Status of this person" field.'))

    source_date = None
    if self.params.source_date:
      try:
        source_date = validate_date(self.params.source_date)
      except ValueError:
        return self.error(400, _('Original posting date is not in YYYY-MM-DD format, or is a nonexistent date.  Please go back and try again.'))
      if source_date > datetime.now():
          return self.error(400, _('Date cannot be in the future.  Please go back and try again.'))
    ### handle image upload ###
    # if picture uploaded, add it and put the generated url
    photo_obj = self.params.photo
    # if image is False, it means it's not a valid image
    if photo_obj == False:
        return self.error(400, _('Photo uploaded is in an unrecognized format.  Please go back and try again.'))

    photo_url = self.params.photo_url
    if photo_obj:
      if max(photo_obj.width, photo_obj.height) <= MAX_IMAGE_DIMENSION:
        # no resize needed...
        # keep the same size but add a transformation so we can change the
        # encoding
        photo_obj.resize(photo_obj.width, photo_obj.width)
      elif photo_obj.width > photo_obj.height:
        photo_obj.resize(MAX_IMAGE_DIMENSION,
                  photo_obj.height * (MAX_IMAGE_DIMENSION / photo_obj.width))
      else:
        photo_obj.resize(
                  photo_obj.width * (MAX_IMAGE_DIMENSION / photo_obj.height),
                  MAX_IMAGE_DIMENSION)

      try:
        sanitized_photo = photo_obj.execute_transforms(
            output_encoding=images.PNG)
      except RequestTooLargeError:
        return self.error(400, _('The provided image is too large.  Please upload a smaller one.'))
      except Exception:
        # There are various images.Error exceptions that can be raised,
        # as well as e.g. IOError if the image is corrupt.
        return self.error(400, _('There was a problem processing the image.  Please try a different image.'))

      photo = Photo(bin_data = sanitized_photo)
      id = db.put(photo)
      #TODO: see if we can create a full url instead of a relative one.
      photo_url = "/photo?id=%s" % (id)

    other = ''
    if self.params.description:
      indented = '    ' + self.params.description.replace('\n', '\n    ')
      indented = indented.rstrip() + '\n'
      other = 'description:\n' + indented

    source_name = self.params.source_name
    if not self.params.clone:
      source_name = (source_name or HOME_DOMAIN)
      source_date = (source_date or datetime.now())

    person = Person(
      entry_date=datetime.now(),
      first_name=self.params.first_name,
      last_name=self.params.last_name,
      sex=self.params.sex,
      date_of_birth=self.params.date_of_birth,
      age=self.params.age,
      home_street=self.params.home_street,
      home_city=self.params.home_city,
      home_state=self.params.home_state,
      home_postal_code=self.params.home_postal_code,
      home_neighborhood=self.params.home_neighborhood,
      home_country=self.params.home_country,
      author_name=self.params.author_name,
      author_phone=self.params.author_phone,
      author_email=self.params.author_email,
      source_url=self.params.source_url,
      source_date=source_date,
      source_name=source_name,
      photo_url=photo_url,
      other=other,
      last_update_date=datetime.now(),
      found=bool(self.params.add_note and self.params.found))

    which_indexing = ['old', 'new']
    person.update_index(which_indexing)

    db.put(person)

    if not person.source_url and not self.params.clone:
      # Create the URL now that we have a person_record_id
      person.source_url = person_page_url('http://' + self.domain, person)
      db.put(person)

    if self.params.add_note:
      note = Note(
        person_record_id=person.person_record_id,
        author_name=self.params.author_name,
        author_phone=self.params.author_phone,
        author_email=self.params.author_email,
        source_date=source_date,
        text=self.params.text,
        last_known_location=self.params.last_known_location,
        status=self.params.status,
        found=bool(self.params.found),
        email_of_found_person=self.params.email_of_found_person,
        phone_of_found_person=self.params.phone_of_found_person)
      db.put(note)

    self.redirect(person_page_url('', person))

if __name__ == '__main__':
  run([('/create', Create)], debug=False)
