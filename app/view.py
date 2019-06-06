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

from google.appengine.api import datastore_errors

from model import *
from utils import *
from detect_spam import SpamDetector
import extend
import reveal
import subscribe

import logging
import pprint

from django.utils.translation import ugettext as _
import urlparse

# how many days left before we warn about imminent expiration.
# Make this at least 1.
EXPIRY_WARNING_THRESHOLD = 7

def get_profile_pages(profile_urls, config, url_builder):
    profile_pages = []
    for profile_url in profile_urls.splitlines():
        # Use the hostname as the website name by default.
        profile_page = {
            'name': urlparse.urlparse(profile_url).hostname,
            'url': profile_url }
        for website in config.profile_websites or []:
            if ('url_regexp' in website and
                re.match(website['url_regexp'], profile_url)):
                profile_page = add_profile_icon_url(website, url_builder)
                profile_page['url'] = profile_url
                break
        profile_pages.append(profile_page)
    return profile_pages

class Handler(BaseHandler):

    def get(self):
        # Check the request parameters.
        if not self.params.id:
            return self.error(404, 'No person id was specified.')
        try:
            person = Person.get(self.repo, self.params.id)
        except ValueError:
            return self.error(404,
                _("This person's entry does not exist or has been deleted."))
        if not person:
            return self.error(404,
                _("This person's entry does not exist or has been deleted."))

        # Check if private info should be revealed.
        content_id = 'view:' + self.params.id
        reveal_url = reveal.make_reveal_url(self, content_id)
        show_private_info = reveal.verify(content_id, self.params.signature)

        # Compute the local times for the date fields on the person.
        person.source_date_local_string = self.to_formatted_local_date(
            person.source_date)
        person.source_time_local_string = self.to_formatted_local_time(
            person.source_date)
        person.expiry_date_local_string = self.to_formatted_local_date(
            person.get_effective_expiry_date())
        person.expiry_time_local_string = self.to_formatted_local_time(
            person.get_effective_expiry_date())

        person.should_show_inline_photo = (
            self.should_show_inline_photo(person.photo_url))

        # Get the notes and duplicate links.
        notes = person.unexpired_notes
        person.sex_text = get_person_sex_text(person)
        for note in notes:
            self.__add_fields_to_note(note)
        try:
            linked_persons = person.get_all_linked_persons()
        except datastore_errors.NeedIndexError:
            linked_persons = []
        linked_person_info = []
        for linked_person in linked_persons:
            try:
                linked_notes = linked_person.get_notes()
            except datastore_errors.NeedIndexError:
                linked_notes = []
            for note in linked_notes:
                self.__add_fields_to_note(note)
            linked_person_info.append(dict(
                id=linked_person.record_id,
                name=linked_person.primary_full_name,
                view_url=self.get_url('/view', id=linked_person.record_id),
                notes=linked_notes))

        # Render the page.
        dupe_notes_url = self.get_url(
            '/view', id=self.params.id, dupe_notes='yes')
        results_url = self.get_url(
            '/results',
            role=self.params.role,
            query_name=self.params.query_name,
            query_location=self.params.query_location,
            given_name=self.params.given_name,
            family_name=self.params.family_name)
        feed_url = self.get_url(
            '/feeds/note',
            person_record_id=self.params.id,
            repo=self.repo)
        subscribe_url = self.get_url('/subscribe', id=self.params.id)
        delete_url = self.get_url('/delete', id=self.params.id)
        extend_url = None
        extension_days = 0
        expiration_days = None
        expiry_date = person.get_effective_expiry_date()
        if expiry_date and not person.is_clone():
            expiration_delta = expiry_date - get_utcnow()
            extend_url =  self.get_url('/extend', id=self.params.id)
            extension_days = extend.get_extension_days(self)
            if expiration_delta.days < EXPIRY_WARNING_THRESHOLD:
                # round 0 up to 1, to make the msg read better.
                expiration_days = expiration_delta.days + 1

        if person.is_clone():
            person.provider_name = person.get_original_domain()

        sanitize_urls(person)
        for note in notes:
            sanitize_urls(note)

        if person.profile_urls:
            person.profile_pages = get_profile_pages(
                person.profile_urls, self.config, self.transitionary_get_url)

        self.render('view.html',
                    person=person,
                    notes=notes,
                    linked_person_info=linked_person_info,
                    onload_function='view_page_loaded',
                    show_private_info=show_private_info,
                    admin=users.is_current_user_admin(),
                    dupe_notes_url=dupe_notes_url,
                    results_url=results_url,
                    reveal_url=reveal_url,
                    feed_url=feed_url,
                    subscribe_url=subscribe_url,
                    delete_url=delete_url,
                    extend_url=extend_url,
                    extension_days=extension_days,
                    expiration_days=expiration_days)

    def __add_fields_to_note(self, note):
        """Adds some fields used in the template to a note."""
        note.status_text = get_note_status_text(note)
        note.linked_person_url = \
            self.get_url('/view', id=note.linked_person_record_id)
        note.flag_spam_url = \
            self.get_url('/flag_note', id=note.note_record_id,
                         hide=(not note.hidden) and 'yes' or 'no',
                         signature=self.params.signature)
        note.source_datetime_local_string = self.to_formatted_local_datetime(
            note.source_date)
        note.should_show_inline_photo = self.should_show_inline_photo(
            note.photo_url)
