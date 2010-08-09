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
import prefix
import reveal
import sys


class Admin(Handler):
  def get(self):
    user = users.get_current_user()
    self.render('templates/admin.html', user=user,
        login_url=users.create_login_url(self.request.url),
        logout_url=users.create_logout_url(self.request.url),
        id=HOME_DOMAIN + '/')

  def post(self):
    if self.params.operation == 'delete':
      # Gather all the entities that are attached to this person.
      person = Person.get_by_person_record_id(self.params.id)
      if not person:
        return self.error(400, 'No person with ID: %r' % self.params.id)

      notes = Note.get_by_person_record_id(self.params.id)
      entities = [person] + notes
      if person.photo_url and person.photo_url.startswith('/photo?id='):
        photo = db.get(person.photo_url.split('=', 1)[1])
        if photo.kind() == 'Photo':
          entities.append(photo)

      if self.params.confirm:
        db.delete(entities)
        return self.error(200, 'The selected entities have been deleted.')
      else:
        return self.render('templates/delete.html',
            params=self.params, person=person, entities=entities)

if __name__ == '__main__':
  run([('/admin', Admin)], debug=False)
