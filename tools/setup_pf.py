# Copyright 2009-2010 by Ka-Ping Yee
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime

import const
from model import *
from utils import *

def setup_datastore():
    """Sets up the subject types and translations in a datastore.  (Existing
    subject types and messages will be updated; existing Subject or Report
    information will not be changed or deleted.)"""
    setup_repos()
    setup_configs()

def wipe_datastore(delete=None, keep=None):
    """Deletes everything in the datastore.  If 'delete' is given (a list of
    kind names), deletes only those kinds of entities.  If 'keep' is given,
    skips deleting those kinds of entities."""
    query = db.Query(keys_only=True)
    keys = query.fetch(1000)
    while keys:
        db.delete([key for key in keys
                   if delete is None or key.kind() in delete
                   if keep is None or key.kind() not in keep])
        keys = query.with_cursor(query.cursor()).fetch(1000)

def reset_datastore():
    """Wipes everything in the datastore except Accounts and Secrets,
    then sets up the datastore for new data."""
    wipe_datastore(keep=['Account', 'Secret'])
    setup_datastore()

def setup_repos():
    db.put([Repo(key_name='haiti'),
            Repo(key_name='japan'),
            Repo(key_name='pakistan')])
    # Set some repositories active so they show on the main page.
    config.set(active_repos=['japan', 'haiti'])

def setup_configs():
    """Installs configuration settings used for testing by server_tests."""
    COMMON_KEYWORDS = ['person', 'people', 'finder', 'person finder',
                       'people finder', 'crisis', 'survivor', 'family']

    # NOTE: the following two CAPTCHA keys are dummy keys for testing only.
    # They should be replaced with real keys upon launch.
    config.set(captcha_private_key='6LfiOr8SAAAAAFyxGzWkhjo_GRXxYoDEbNkt60F2',
               captcha_public_key='6LfiOr8SAAAAAM3wRtnLdgiVfud8uxCqVVJWCs-z',
    # A Google Translate API key with a very low quota, just for testing.
               translate_api_key='AIzaSyCXdz9x7LDL3BvieEP8Wcze64CC_iqslSE')

    config.set_for_repo(
        'haiti',
        # Appended to "Google Person Finder" in page titles.
        repo_titles={
            'en': 'Haiti Earthquake',
            'fr': u'S\xe9isme en Ha\xefti',
            'ht': u'Tranbleman T\xe8 an Ayiti',
            'es': u'Terremoto en Hait\xed'
        },
        # List of language codes that appear in the language menu.
        language_menu_options=['en', 'ht', 'fr', 'es'],
        # Content for the <meta name="keywords"> tag.
        keywords=', '.join([
            'haiti', 'earthquake', 'haiti earthquake', 'haitian',
            u'ha\xefti', u's\xe9isme', 'tremblement', 'tremblement de terre',
            'famille', 'recherche de personnes', 'terremoto'
        ] + COMMON_KEYWORDS),
        # If false, hide the family_name field and use only given_name.
        use_family_name=True,
        # Presentation order for the given name and family name.
        family_name_first=False,
        # If true, show extra fields for alternate names.
        use_alternate_names=True,
        # If false, hide the home_zip field.
        use_postal_code=True,
        # Require at least this many letters in each word of a text query.
        min_query_word_length=2,
        # Show input fields for profile URLs in create page.
        show_profile_entry=True,
        # Default list of profile websites to show in create page.
        profile_websites=const.DEFAULT_PROFILE_WEBSITES,
        # Default map viewport for the location field in the note form.
        map_default_zoom=7,
        map_default_center=[18.968637, -72.284546],
        map_size_pixels=[400, 280],
        # If true, the feeds and read API require an authorization key.
        read_auth_key_required=False,
        # If true, the search API requires an authorization key.
        search_auth_key_required=False,
        # If true, show "believed dead" option in the note status dropdown
        allow_believed_dead_via_ui=True,
        # Custom html messages to show on main page, results page, view page,
        # and query form, keyed by language codes.
        start_page_custom_htmls={'en': '', 'fr': ''},
        results_page_custom_htmls={'en': '', 'fr': ''},
        view_page_custom_htmls={'en': '', 'fr': ''},
        seek_query_form_custom_htmls={'en': '', 'fr': ''},
        published_date=get_timestamp(datetime(2010, 1, 12)),
        updated_date=get_timestamp(datetime(2010, 1, 12)),
    )

    config.set_for_repo(
        'japan',
        language_menu_options=['ja', 'en', 'ko', 'zh-CN', 'zh-TW', 'pt-BR', 'es'],
        repo_titles={
            'en': '2011 Japan Earthquake',
            'zh-TW': u'2011 \u65e5\u672c\u5730\u9707',
            'zh-CN': u'2011 \u65e5\u672c\u5730\u9707',
            'pt-BR': u'2011 Terremoto no Jap\xe3o',
            'ja': u'2011 \u65e5\u672c\u5730\u9707',
            'es': u'2011 Terremoto en Jap\xf3n'
        },
        keywords=', '.join(COMMON_KEYWORDS),
        use_family_name=True,
        family_name_first=True,
        use_alternate_names=True,
        use_postal_code=True,
        min_query_word_length=1,
        show_profile_entry=True,
        profile_websites=const.DEFAULT_PROFILE_WEBSITES,
        map_default_zoom=7,
        map_default_center=[38, 140.7],
        map_size_pixels=[400, 400],
        search_auth_key_required=True,
        read_auth_key_required=True,
        allow_believed_dead_via_ui=True,
        start_page_custom_htmls={'en': 'Custom message', 'fr': 'French'},
        results_page_custom_htmls={'en': 'Custom message', 'fr': 'French'},
        view_page_custom_htmls={'en': 'Custom message', 'fr': 'French'},
        seek_query_form_custom_htmls={'en': '', 'fr': ''},
        # NOTE(kpy): These two configuration settings only work for locations
        # with a single, fixed time zone offset and no Daylight Saving Time.
        time_zone_offset=9,  # UTC+9
        time_zone_abbreviation='JST',
        jp_mobile_carrier_redirect=True,
        jp_tier2_mobile_redirect_url='http://sagasu-m.appspot.com',
        published_date=get_timestamp(datetime(2011, 3, 11)),
        updated_date=get_timestamp(datetime(2011, 3, 11)),
    )

    config.set_for_repo(
        'pakistan',
        repo_titles={
            'en': 'Pakistan Floods',
            'ur': u'\u067e\u0627\u06a9\u0633\u062a\u0627\u0646\u06cc \u0633\u06cc\u0644\u0627\u0628'
        },
        language_menu_options=['en', 'ur'],
        keywords=', '.join([
            'pakistan', 'flood', 'pakistan flood', 'pakistani'
        ] + COMMON_KEYWORDS),
        use_family_name=False,
        family_name_first=False,
        use_alternate_names=False,
        use_postal_code=False,
        min_query_word_length=1,
        map_default_zoom=6,
        map_default_center=[33.36, 73.26],  # near Rawalpindi, Pakistan
        map_size_pixels=[400, 500],
        read_auth_key_required=False,
        search_auth_key_required=False,
        allow_believed_dead_via_ui=True,
        start_page_custom_htmls={'en': '', 'fr': ''},
        results_page_custom_htmls={'en': '', 'fr': ''},
        view_page_custom_htmls={'en': '', 'fr': ''},
        seek_query_form_custom_htmls={'en': '', 'fr': ''},
        published_date=get_timestamp(datetime(2010, 8, 6)),
        updated_date=get_timestamp(datetime(2010, 8, 6)),
    )

def setup_lang_test_config():
    config.set_for_repo(
        'lang-test',
        # We set short titles to avoid exceeding the field's 500-char limit.
        repo_titles=dict((lang, lang) for lang in const.LANGUAGE_ENDONYMS),
        language_menu_options=list(const.LANGUAGE_ENDONYMS.keys()),
        keywords=', '.join(COMMON_KEYWORDS),
        use_family_name=True,
        family_name_first=True,
        use_alternate_names=True,
        use_postal_code=True,
        min_query_word_length=1,
        map_default_zoom=6,
        map_default_center=[0 ,0],
        map_size_pixels=[400, 500],
        read_auth_key_required=False,
        search_auth_key_required=False,
        allow_believed_dead_via_ui=True,
        start_page_custom_htmls={'en': '', 'fr': ''},
        results_page_custom_htmls={'en': '', 'fr': ''},
        view_page_custom_htmls={'en': '', 'fr': ''},
        seek_query_form_custom_htmls={'en': '', 'fr': ''},
    )
