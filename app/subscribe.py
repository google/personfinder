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

from google.appengine.ext import db
from google.appengine.api import taskqueue

import config
import model
import reveal
from utils import *

from django.utils.html import escape
from django.utils.translation import ugettext as _

EMAIL_PATTERN = re.compile(r'(?:^|\s)[-a-z0-9_.%$+]+@(?:[-a-z0-9]+\.)+'
                           '[a-z]{2,6}(?:\s|$)', re.IGNORECASE)

def is_email_valid(email):
    """Validates an email address, returning True on correct,
    False on incorrect, None on empty string."""
    # Note that google.appengine.api.mail.is_email_valid() is unhelpful;
    # it checks only for the empty string
    if not email:
        return None
    if EMAIL_PATTERN.match(email):
        return True
    else:
        return False


def get_unsubscribe_link(handler, person, email, ttl=7*24*3600):
    """Returns a link that will remove the given email address from the list
    of subscribers for the given person, default ttl is one week"""
    data = 'unsubscribe:%s' % email
    token = reveal.sign(data, ttl)
    return handler.get_url('/unsubscribe', token=token, email=email,
                           id=person.record_id)

def subscribe_to(handler, repo, person, email, lang):
    """Add a subscription on a person for an e-mail address"""
    existing = model.Subscription.get(repo, person.record_id, email)
    if existing and existing.language == lang:
        return None

    if existing:
        subscription = existing
        subscription.language = lang
    else:
        subscription = model.Subscription.create(
            repo, person.record_id, email, lang)
    db.put(subscription)
    send_subscription_confirmation(handler, person, email)
    return subscription

def send_notifications(handler, updated_person, notes, follow_links=True):
    """Sends status updates about the person

    Subscribers to the updated_person and to all person records marked as its
    duplicate will be notified. Each element of notes should belong to the
    updated_person. If follow_links=False, only notify subscribers to the
    updated_person, ignoring linked Person records.
    """
    linked_persons = []
    if follow_links:
        linked_persons = updated_person.get_all_linked_persons()
    # Dictionary of
    # (subscriber_email, [person_subscribed_to, subscriber_language]) pairs
    subscribers = {}
    # Subscribers to duplicates of updated_person
    for p in linked_persons:
        for sub in p.get_subscriptions():
            subscribers[sub.email] = [p, sub.language]
    # Subscribers to updated_person
    for sub in updated_person.get_subscriptions():
        subscribers[sub.email] = [updated_person, sub.language]
    try:
        for note in notes:
            if note.person_record_id != updated_person.record_id:
                continue
            for email, (subscribed_person, language) in subscribers.items():
                subscribed_person_url = \
                    handler.get_url('/view', id=subscribed_person.record_id)
                if is_email_valid(email):
                    django.utils.translation.activate(language)
                    subject = _(
                            '[Person Finder] Status update for %(full_name)s'
                            ) % {'full_name': updated_person.primary_full_name}
                    body = handler.render_to_string(
                        'person_status_update_email.txt', language,
                        full_name=updated_person.primary_full_name,
                        note=note,
                        note_status_text=get_note_status_text(note),
                        subscribed_person_url=subscribed_person_url,
                        site_url=handler.get_url('/'),
                        view_url=handler.get_url('/view',
                                                 id=updated_person.record_id),
                        unsubscribe_link=get_unsubscribe_link(handler,
                                                              subscribed_person,
                                                              email))
                    handler.send_mail(email, subject, body)
    finally:
        django.utils.translation.activate(handler.env.lang)

def send_subscription_confirmation(handler, person, email):
    """Sends subscription confirmation when person subscribes to
    status updates"""
    subject = _('[Person Finder] You are subscribed to status updates for '
            '%(full_name)s') % {'full_name': escape(person.primary_full_name)}
    body = handler.render_to_string(
        'subscription_confirmation_email.txt',
        full_name=person.primary_full_name,
        site_url=handler.get_url('/'),
        view_url=handler.get_url('/view', id=person.record_id),
        unsubscribe_link=get_unsubscribe_link(handler, person, email))
    handler.send_mail(email, subject, body)


class Handler(BaseHandler):
    """Handles requests to subscribe to notifications on Person and
    Note record updates."""
    def get(self):
        person = model.Person.get(self.repo, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        form_action = self.get_url('/subscribe', id=self.params.id)
        back_url = self.get_url('/view', id=self.params.id)
        site_key = config.get('captcha_site_key')
        self.render('subscribe_captcha.html',
                    site_key=site_key,
                    person=person,
                    captcha_html=self.get_captcha_html(),
                    subscribe_email=self.params.subscribe_email or '',
                    form_action=form_action,
                    back_url=back_url,
                    person_record_link_html=
                        self.__get_person_record_link_html(person),
                    context=self.params.context)

    def post(self):
        person = model.Person.get(self.repo, self.params.id)
        if not person:
            return self.error(400, 'No person with ID: %r' % self.params.id)

        if not is_email_valid(self.params.subscribe_email):
            # Invalid email
            captcha_html = self.get_captcha_html()
            site_key = config.get('captcha_site_key')
            form_action = self.get_url('/subscribe', id=self.params.id)
            return self.render('subscribe_captcha.html',
                               person=person,
                               site_key=site_key,
                               subscribe_email=self.params.subscribe_email,
                               message=_(
                                   'Invalid e-mail address. Please try again.'),
                               captcha_html=captcha_html,
                               form_action=form_action,
                               person_record_link_html=
                                   self.__get_person_record_link_html(person))

        # Check the captcha
        captcha_response = self.get_captcha_response()
        if not captcha_response.is_valid:
            # Captcha is incorrect
            captcha_html = self.get_captcha_html(captcha_response.error_code)
            site_key = config.get('captcha_site_key')
            form_action = self.get_url('/subscribe', id=self.params.id)
            return self.render('subscribe_captcha.html',
                               person=person,
                               site_key=site_key,
                               subscribe_email=self.params.subscribe_email,
                               captcha_html=captcha_html,
                               form_action=form_action,
                               person_record_link_html=
                                   self.__get_person_record_link_html(person))

        subscription = subscribe_to(self, self.repo, person,
                                    self.params.subscribe_email, self.env.lang)
        if not subscription:
            # User is already subscribed
            url = self.get_url('/view', id=self.params.id)
            link_text = _('Return to the record for %(full_name)s.'
                    ) % {'full_name': escape(person.primary_full_name)}
            html = '<a href="%s">%s</a>' % (url, link_text)
            message_html = _('You are already subscribed. ' + html)
            return self.info(200, message_html=message_html)

        url = self.get_url('/view', id=self.params.id)
        link_text = _('Return to the record for %(full_name)s.'
                ) % {'full_name': escape(person.primary_full_name)}
        html = ' <a href="%s">%s</a>' % (url, link_text)
        message_html = _('You have successfully subscribed.') + html
        return self.info(200, message_html=message_html)

    def __get_person_record_link_html(self, person):
        return '<a href="%s" target=_blank>%s</a>' % (
            django.utils.html.escape(self.get_url('/view', id=person.person_record_id)),
            django.utils.html.escape(person.primary_full_name))
