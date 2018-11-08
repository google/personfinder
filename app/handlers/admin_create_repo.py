#!/usr/bin/python2.7
# Copyright 2016 Google Inc.
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


from const import *
from model import *
from utils import *


class Handler(BaseHandler):
    """An admin page to create a repository."""

    repo_required = False
    admin_required = True

    def get(self):
        self.render('admin_create_repo.html')

    def post(self):
        new_repo = self.params.new_repo
        Repo(key_name=new_repo).put()
        config.set_for_repo(  # Provide some defaults.
            new_repo,
            language_menu_options=['en', 'fr'],
            repo_titles={'en': 'Earthquake', 'fr': u'S\xe9isme'},
            keywords='person finder, people finder, person, people, ' +
                'crisis, survivor, family',
            use_family_name=True,
            use_alternate_names=True,
            use_postal_code=True,
            allow_believed_dead_via_ui=False,
            min_query_word_length=2,
            show_profile_entry=False,
            profile_websites=DEFAULT_PROFILE_WEBSITES,
            map_default_zoom=6,
            map_default_center=[0, 0],
            map_size_pixels=[400, 280],
            read_auth_key_required=True,
            search_auth_key_required=True,
            deactivated=False,
            launched=False,
            deactivation_message_html='',
            start_page_custom_htmls={'en': '', 'fr': ''},
            results_page_custom_htmls={'en': '', 'fr': ''},
            view_page_custom_htmls={'en': '', 'fr': ''},
            seek_query_form_custom_htmls={'en': '', 'fr': ''},
            footer_custom_htmls={'en': '', 'fr': ''},
            bad_words='',
            published_date=get_utcnow_timestamp(),
            updated_date=get_utcnow_timestamp(),
            test_mode=False,
            force_https=False,
            zero_rating_mode=False,
            time_zone_offset=0,
            time_zone_abbreviation='UTC',
        )
        self.redirect('/admin', new_repo)
