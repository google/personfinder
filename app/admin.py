#!/usr/bin/python2.5
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


from datetime import datetime
import simplejson
import sys

from model import *
from utils import *
import reveal

class Admin(Handler):
    # After a subdomain is deactivated, we still need the admin page to be
    # accessible so we can edit its settings.
    ignore_deactivation = True
    
    def get(self):
        user = users.get_current_user()
        simplejson.encoder.FLOAT_REPR = str
        encoder = simplejson.encoder.JSONEncoder(ensure_ascii=False)
        config_json = dict((name, encoder.encode(self.config[name]))
                           for name in self.config.keys())
        #sorts languages by exonym; to sort by code, remove the key argument
        sorted_exonyms = sorted(list(LANGUAGE_EXONYMS.items()),
                                key= lambda lang: lang[1])
        sorted_exonyms = map(lambda elem: {'code' : elem[0],
                                           'exonym' : elem[1]}, sorted_exonyms)
        sorted_exonyms_json = encoder.encode(sorted_exonyms)
        self.render('templates/admin.html', user=user,
                    subdomains=Subdomain.all(),
                    config=self.config, config_json=config_json,
                    start_url=self.get_start_url(),
                    login_url=users.create_login_url(self.request.url),
                    logout_url=users.create_logout_url(self.request.url),
                    language_exonyms_json=sorted_exonyms_json,
                    onload_function="add_initial_languages()",
                    id=self.env.domain + '/person.')

    def post(self):
        if self.params.operation == 'delete':
            # Redirect to the deletion handler with a valid signature.
            action = ('delete', str(self.params.id))
            self.redirect('/delete', id=self.params.id,
                          signature=reveal.sign(action))

        elif self.params.operation == 'subdomain_create':
            Subdomain(key_name=self.params.subdomain_new).put()
            config.set_for_subdomain(  # Provide some defaults.
                self.params.subdomain_new,
                language_menu_options=['en', 'fr'],
                subdomain_titles={'en': 'Earthquake', 'fr': u'S\xe9isme'},
                keywords='person finder, people finder, person, people, ' +
                    'crisis, survivor, family',
                use_family_name=True,
                use_alternate_names=True,
                use_postal_code=True,
                min_query_word_length=2,
                map_default_zoom=6,
                map_default_center=[0, 0],
                map_size_pixels=[400, 280],
                read_auth_key_required=True,
                search_auth_key_required=True,
                deactivated=False,
                deactivation_message_html='',
                main_page_custom_htmls={'en': '', 'fr': ''},
                results_page_custom_htmls={'en': '', 'fr': ''},
                view_page_custom_htmls={'en': '', 'fr': ''},
                seek_query_form_custom_htmls={'en': '', 'fr': ''},
            )
            self.redirect('/admin', subdomain=self.params.subdomain_new)

        elif self.params.operation == 'subdomain_save':
            values = {}
            for name in [  # These settings are all entered in JSON.
                'language_menu_options', 'subdomain_titles',
                'use_family_name', 'family_name_first', 'use_alternate_names',
                'use_postal_code', 'min_query_word_length', 'map_default_zoom',
                'map_default_center', 'map_size_pixels',
                'read_auth_key_required', 'search_auth_key_required',
                'deactivated', 'main_page_custom_htmls',
                'results_page_custom_htmls', 'view_page_custom_htmls',
                'seek_query_form_custom_htmls',
            ]:
                try:
                    values[name] = simplejson.loads(self.request.get(name))
                except:
                    return self.error(
                        400, 'The setting for %s was not valid JSON.' % name)

            for name in ['keywords', 'deactivation_message_html']:
                # These settings are literal strings (not JSON).
                values[name] = self.request.get(name)

            config.set_for_subdomain(self.subdomain, **values)
            self.redirect('/admin', subdomain=self.subdomain)

if __name__ == '__main__':
    run(('/admin', Admin))
