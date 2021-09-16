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

from model import *
import photo
from utils import *
from detect_spam import SpamDetector
from recaptcha.client import captcha
import subscribe
import simplejson

from django.core.validators import URLValidator, ValidationError
from django.utils.translation import ugettext as _

import const

def validate_date(string):
    """Parses a date in YYYY-MM-DD format.    This is a special case for manual
    entry of the source_date in the creation form.    Unlike the validators in
    utils.py, this will throw an exception if the input is badly formatted."""
    year, month, day = map(int, string.strip().split('-'))
    return datetime(year, month, day)

def days_to_date(days):
    """Converts a duration signifying days-from-now to a datetime object.

    Returns:
      None if days is None, else now + days (in utc)"""
    return days and get_utcnow() + timedelta(days=days)


class CreationError(Exception):

    def __init__(self, user_readable_message, message=None):
        super(CreationError, self).__init__(message)
        self.user_readable_message = user_readable_message

class FlaggedNoteException(Exception):

    def __init__(self, note, message=None):
        super(FlaggedNoteException, self).__init__(message)
        self.note = note


def create_person(
        repo,
        config,
        user_ip_address,
        given_name,
        family_name,
        own_info,
        clone,
        status,
        source_name,
        source_url,
        source_date,
        referrer,
        author_name,
        author_email,
        author_phone,
        author_made_contact,
        users_own_email,
        users_own_phone,
        alternate_given_names,
        alternate_family_names,
        home_neighborhood,
        home_city,
        home_state,
        home_postal_code,
        home_country,
        age,
        sex,
        description,
        person_photo,
        person_photo_url,
        note_photo,
        note_photo_url,
        profile_urls,
        add_note,
        text,
        email_of_found_person,
        phone_of_found_person,
        last_known_location,
        url_builder,
        source_domain=const.HOME_DOMAIN,
        should_fuzzify_age=True,
        expiry_option=None):
    now = get_utcnow()
    if config.use_family_name:
        if not (given_name and family_name):
            raise CreationError(_(
                'The Given name and Family name are both required.  Please go '
                'back and try again.'))
    else:
        if not given_name:
            raise CreationError(_(
                'Name is required.  Please go back and try again.'))

    # If user is inputting his/her own information, set some params automatically
    if own_info == 'yes':
        author_name = given_name
        status = 'is_note_author'
        author_made_contact = 'yes'
        if users_own_email:
            author_email = users_own_email
        if users_own_phone:
            author_phone = users_own_phone

    if (author_email and not validate_email(author_email)):
        raise CreationError(_(
            'The email address you entered appears to be invalid.'))

    else:
        if not author_name:
            if clone:
                raise CreationError(_(
                    'The Original author\'s name is required.  Please go back '
                    'and try again.'))
            else:
                raise CreationError(_(
                    'Your name is required in the "Source" section.  Please go '
                    'back and try again.'))

    if add_note:
        validate_note_data(
            config=config,
            status=status,
            author_name=author_name,
            author_email=author_email,
            author_made_contact=author_made_contact,
            text=text)

    if source_date:
        try:
            source_date = validate_date(source_date)
        except ValueError:
            raise CreationError(_(
                'Original posting date is not in YYYY-MM-DD format, or is a '
                'nonexistent date.  Please go back and try again.'))
        if source_date > now:
            raise CreationError(_(
                'Date cannot be in the future.  Please go back and try again.'))

    expiry_date = days_to_date(expiry_option or config.default_expiry_days)

    profile_urls = profile_urls or []
    profile_urls = filter(lambda url: url, profile_urls)
    url_validator = URLValidator(schemes=['http', 'https'])
    for profile_url in profile_urls:
        try:
            url_validator(profile_url)
        except ValidationError:
            raise CreationError(_('Please only enter valid profile URLs.'))

    # If nothing was uploaded, just use the photo URL that was provided.
    try:
        # If a photo was uploaded, create a Photo entry and get the URL
        # where we serve it.
        if person_photo is not None:
            person_photo, person_photo_url = photo.create_photo(
                person_photo, repo, url_builder)
        if note_photo is not None:
            note_photo, note_photo_url = photo.create_photo(
                note_photo, repo, url_builder)
    except photo.PhotoError as e:
        raise CreationError(e.message)
    # Finally, store the Photo. Past this point, we should NOT self.error.
    if person_photo:
        person_photo.put()
    if note_photo:
        note_photo.put()

    # Person records have to have a source_date; if none entered, use now.
    source_date = source_date or now

    # Determine the source name, or fill it in if the record is original
    # (i.e. created for the first time here, not copied from elsewhere).
    if not clone:
        # record originated here
        if referrer:
            source_name = "%s (referred by %s)" % (source_domain, referrer)
        else:
            source_name = source_domain

    if age and should_fuzzify_age:
        age = fuzzify_age(age)
    person = Person.create_original(
        repo,
        entry_date=now,
        expiry_date=expiry_date,
        given_name=given_name,
        family_name=family_name,
        full_name=get_full_name(given_name, family_name, config),
        alternate_names=get_full_name(
            alternate_given_names or '', alternate_family_names or '', config),
        description=description,
        sex=sex,
        age=age,
        home_city=home_city,
        home_state=home_state,
        home_postal_code=home_postal_code,
        home_neighborhood=home_neighborhood,
        home_country=home_country,
        profile_urls='\n'.join(profile_urls),
        author_name=author_name,
        author_phone=author_phone,
        author_email=author_email,
        source_url=source_url,
        source_date=source_date,
        source_name=source_name,
        photo=person_photo,
        photo_url=person_photo_url
    )
    person.update_index(['old', 'new'])

    if add_note:
        try:
            note = create_note(
                repo=repo,
                person=person,
                config=config,
                user_ip_address=user_ip_address,
                status=status,
                source_date=source_date,
                author_name=author_name,
                author_email=author_email,
                author_phone=author_phone,
                author_made_contact=bool(author_made_contact),
                note_photo=note_photo,
                note_photo_url=note_photo_url,
                text=text,
                email_of_found_person=email_of_found_person,
                phone_of_found_person=phone_of_found_person,
                last_known_location=last_known_location,
                # We called validate_note_data separately above.
                validate_data=False)
        except FlaggedNoteException as e:
            db.put(person)
            UserActionLog.put_new('add', person, copy_properties=False)
            # When the note is detected as spam, we do not update person
            # record with this note or log action. We ask the note author
            # for confirmation first.
            raise e

        person.update_from_note(note)

        # Specially log 'believed_dead'.
        if note.status == 'believed_dead':
            UserActionLog.put_new(
                'mark_dead', note, person.primary_full_name,
                user_ip_address)

    # Write the person record to datastore
    person.put_new()

    # TODO(ryok): we could do this earlier so we don't neet to db.put twice.
    if not person.source_url and not clone:
        # Put again with the URL, now that we have a person_record_id.
        person.source_url = url_builder(
            '/view', repo, params={'id': person.record_id})
        db.put(person)

    # TODO(ryok): batch-put person, note, photo, note_photo here.

    return person


def validate_note_data(
        config,
        status,
        author_name,
        author_email,
        author_made_contact,
        text):
    if not text:
        raise CreationError(_(
            'Message is required. Please go back and try again.'))
    if not author_name:
        raise CreationError(_(
            'Your name is required in the "About you" section.  Please go back '
            'and try again.'))
    if status == 'is_note_author' and not author_made_contact:
        raise CreationError(_(
            'Please check that you have been in contact with the person after '
            'the disaster, or change the "Status of this person" field.'))
    if status == 'believed_dead' and not config.allow_believed_dead_via_ui:
        raise CreationError(_(
            'Not authorized to post notes with the status "believed_dead".'))
    if author_email and not validate_email(author_email):
        raise CreationError(_(
            'The email address you entered appears to be invalid.'))


def create_note(
        repo,
        person,
        config,
        user_ip_address,
        status,
        source_date,
        author_name,
        author_email,
        author_phone,
        author_made_contact,
        note_photo,
        note_photo_url,
        text,
        email_of_found_person,
        phone_of_found_person,
        last_known_location,
        validate_data=True):
    if validate_data:
        validate_note_data(
            config=config,
            status=status,
            author_name=author_name,
            author_email=author_email,
            author_made_contact=author_made_contact,
            text=text)
    spam_detector = SpamDetector(config.bad_words)
    spam_score = spam_detector.estimate_spam_score(text)
    if spam_score > 0:
        note = NoteWithBadWords.create_original(
            repo,
            entry_date=get_utcnow(),
            person_record_id=person.record_id,
            author_name=author_name,
            author_email=author_email,
            author_phone=author_phone,
            source_date=source_date,
            author_made_contact=author_made_contact,
            status=status,
            email_of_found_person=email_of_found_person,
            phone_of_found_person=phone_of_found_person,
            last_known_location=last_known_location,
            text=text,
            photo=note_photo,
            photo_url=note_photo_url,
            spam_score=spam_score,
            confirmed=False)
        note.put_new()
        raise FlaggedNoteException(note)
    note = Note.create_original(
        repo,
        entry_date=get_utcnow(),
        person_record_id=person.record_id,
        author_name=author_name,
        author_email=author_email,
        author_phone=author_phone,
        source_date=source_date,
        author_made_contact=author_made_contact,
        status=status,
        email_of_found_person=email_of_found_person,
        phone_of_found_person=phone_of_found_person,
        last_known_location=last_known_location,
        text=text,
        photo=note_photo,
        photo_url=note_photo_url)
    note.put_new()
    # Specially log notes that make a person dead or switch to an alive status.
    if status == 'believed_dead':
        UserActionLog.put_new(
            'mark_dead', note, person.record_id, user_ip_address)
    if (status in ['believed_alive', 'is_note_author'] and
            person.latest_status not in ['believed_alive', 'is_note_author']):
        UserActionLog.put_new('mark_alive', note, person.record_id)
    # TODO(nworden): add sending subscription notifications here
    return note


class Handler(BaseHandler):
    def _render_create_html(self):
        self.params.create_mode = True
        profile_websites = [
            add_profile_icon_url(website, self.transitionary_get_url)
            for website in self.config.profile_websites or []]
        self.render('create.html',
                    captcha_html=self.get_captcha_html(),
                    profile_websites=profile_websites,
                    profile_websites_json=simplejson.dumps(profile_websites),
                    onload_function='view_page_loaded')

    def get(self):
        self._render_create_html()

    def post(self):
        captcha_response = self.get_captcha_response()
        if not captcha_response.is_valid:
            self._render_create_html()
            return

        profile_urls = [self.params.profile_url1,
                        self.params.profile_url2,
                        self.params.profile_url3]
        try:
            person = create_person(
                repo=self.repo,
                config=self.config,
                user_ip_address=self.request.remote_addr,
                given_name=self.params.given_name,
                family_name=self.params.family_name,
                own_info=self.params.own_info,
                clone=self.params.clone,
                status=self.params.status,
                source_name=self.params.source_name,
                source_url=self.params.source_url,
                source_date=self.params.source_date,
                referrer=self.params.referrer,
                author_name=self.params.author_name,
                author_email=self.params.author_email,
                author_phone=self.params.author_phone,
                author_made_contact=self.params.author_made_contact,
                users_own_email=self.params.your_own_email,
                users_own_phone=self.params.your_own_phone,
                alternate_given_names=self.params.alternate_given_names,
                alternate_family_names=self.params.alternate_family_names,
                home_neighborhood=self.params.home_neighborhood,
                home_city=self.params.home_city,
                home_state=self.params.home_state,
                home_postal_code=self.params.home_postal_code,
                home_country=self.params.home_country,
                age=self.params.age,
                sex=self.params.sex,
                description=self.params.description,
                person_photo=self.params.photo,
                person_photo_url=self.params.photo_url,
                note_photo=self.params.note_photo,
                note_photo_url=self.params.note_photo_url,
                profile_urls=profile_urls,
                add_note=self.params.add_note,
                text=self.params.text,
                email_of_found_person=self.params.email_of_found_person,
                phone_of_found_person=self.params.phone_of_found_person,
                last_known_location=self.params.last_known_location,
                source_domain=self.env.netloc,
                expiry_option=self.params.expiry_option,
                url_builder=self.transitionary_get_url)
        except FlaggedNoteException as e:
            return self.redirect('/post_flagged_note',
                                 id=e.note.get_record_id(),
                                 author_email=e.note.author_email,
                                 repo=self.repo)
        except CreationError as e:
            return self.error(400, e.user_readable_message)

        # if unchecked the subscribe updates about your own record, skip the subscribe page
        if not self.params.subscribe_own_info:
            self.params.subscribe = False

        # If user wants to subscribe to updates, redirect to the subscribe page
        if self.params.subscribe:
            return self.redirect('/subscribe',
                                 id=person.record_id,
                                 subscribe_email=self.params.author_email,
                                 context='create_person')

        self.redirect('/view', id=person.record_id)
