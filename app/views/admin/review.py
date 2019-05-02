# Copyright 2019 Google Inc.
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
"""The admin content review page."""

import django.shortcuts
from google.appengine.ext import db

import const
import model
import utils
import views.admin.base


class AdminReviewView(views.admin.base.AdminBaseView):
    """The admin review view."""

    ACTION_ID = 'admin/review'

    _NOTES_PER_PAGE = 50

    _STATUS_OPTIONS = [
        'all',
        'unspecified',
        'information_sought',
        'is_note_author',
        'believed_alive',
        'believed_missing',
        'believed_dead',
    ]

    _STATUS_CODES = {
        None: 'u',
        '': 'u',
        'information_sought': 's',
        'believed_alive': 'a',
        'believed_missing': 'm',
        'believed_dead': 'd',
        'is_note_author': 'i',
    }

    def setup(self, request, *args, **kwargs):
        super(AdminReviewView, self).setup(request, *args, **kwargs)
        self.params.read_values(
            get_params={
                'skip': utils.validate_int,
                'source': utils.strip,
                'status': utils.strip,
            },
            post_params={
                'skip': utils.validate_int,
                'source': utils.strip,
                'status': utils.strip,
            }
        )

    @views.admin.base.enforce_moderator_admin_level
    def get(self, request, *args, **kwargs):
        """Serves GET requests."""
        del request, args, kwargs  # unused

        current_selected_status = self.params.status or 'all'
        current_selected_source = self.params.source or 'all'
        status_options_nav = []
        for option in AdminReviewView._STATUS_OPTIONS:
            if option == current_selected_status:
                status_options_nav.append((option, None))
            else:
                option_url = self.build_absolute_path(
                    '/admin/review', self.env.repo,
                    params=[
                        ('status', option),
                        ('source', current_selected_source),
                    ])
                status_options_nav.append((option, option_url))
        source_options = ['all', '%s.%s' % (self.env.repo, const.HOME_DOMAIN)]
        for auth_key in model.Authorization.all().filter(
                'repo =', self.env.repo):
            if auth_key.domain_write_permission:
                source_options.append(auth_key.domain_write_permission)
        source_options_nav = []
        for option in source_options:
            if option == current_selected_source:
                source_options_nav.append((option, None))
            else:
                option_url = self.build_absolute_path(
                    '/admin/review', self.env.repo,
                    params=[
                        ('source', option),
                        ('status', current_selected_status),
                    ])
                source_options_nav.append((option, option_url))

        query = model.Note.all_in_repo(self.env.repo)
        query = query.filter('reviewed =', False).filter('hidden =', False)
        if current_selected_status == 'unspecified':
            query.filter('status =', '')
        elif current_selected_status != 'all':
            query.filter('status =', current_selected_status)
        if current_selected_source != 'all':
            query.filter('person_record_id >=', '%s/' % current_selected_source)
            query.filter('person_record_id <', '%s0' % current_selected_source)
            # TODO(ryok): we really want to order by entry_date, but GAE
            # restriction applies here, and we can not use two different
            # properties for comparison and ordering. The proper solution seems
            # to add a property source_domain to Note.
            query.order('-person_record_id')
        else:
            query.order('-entry_date')

        skip = self.params.skip or 0
        notes = query.fetch(AdminReviewView._NOTES_PER_PAGE + 1, skip)
        for note in notes[:AdminReviewView._NOTES_PER_PAGE]:
            person = model.Person.get(self.env.repo, note.person_record_id)
            if person:
                # Copy in the fields of the associated Person.
                for name in person.properties():
                    setattr(note, 'person_' + name, getattr(person, name))

                # Get the statuses of the other notes on this Person.
                status_codes = ''
                for other_note in person.get_notes():
                    code = AdminReviewView._STATUS_CODES[other_note.status]
                    if other_note.note_record_id == note.note_record_id:
                        code = code.upper()
                    status_codes += code
                note.person_status_codes = status_codes

        if len(notes) > AdminReviewView._NOTES_PER_PAGE:
            notes = notes[:AdminReviewView._NOTES_PER_PAGE]
            next_skip = skip + AdminReviewView._NOTES_PER_PAGE
            next_url = self.build_absolute_path(
                '/admin/review', self.env.repo,
                params=[
                    ('skip', str(next_skip)),
                    ('source', current_selected_source),
                    ('status', current_selected_status),
                ])
        else:
            next_url = None

        return self.render(
            'admin_review.html',
            notes=notes,
            next_url=next_url,
            first=skip+1,
            last=skip+len(notes[:AdminReviewView._NOTES_PER_PAGE]),
            source_options_nav=source_options_nav,
            status_options_nav=status_options_nav,
            xsrf_token=self.xsrf_tool.generate_token(
                self.env.user.user_id(), self.ACTION_ID))

    @views.admin.base.enforce_moderator_admin_level
    def post(self, request, *args, **kwargs):
        """Serves POST requests, creating a new repo."""
        del request, args, kwargs  # unused
        self.enforce_xsrf(self.ACTION_ID)

        notes = []
        for param_key, value in self.request.POST.items():
            if param_key.startswith('note.'):
                note = model.Note.get(self.env.repo, param_key[5:])
                if note:
                    if value in ['accept', 'flag']:
                        note.reviewed = True
                    if value == 'flag':
                        note.hidden = True
                    notes.append(note)
        db.put(notes)

        return django.shortcuts.redirect(self.build_absolute_path())
