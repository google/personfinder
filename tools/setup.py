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

from model import *
from utils import *

def setup_datastore():
    """Sets up the subject types and translations in a datastore.  (Existing
    subject types and messages will be updated; existing Subject or Report
    information will not be changed or deleted.)"""
    setup_subdomains()
    setup_configs()

def wipe_datastore(*kinds):
    """Deletes everything in the datastore except Accounts and Secrets.
    If 'kinds' is given, deletes only those kinds of entities."""
    for kind in kinds or [Person, Note, Photo, Authorization,
                          Subdomain, config.ConfigEntry, UserActionLog]:
        options = {'keys_only': True}
        if kind in [Person, Note]:  # Clean out expired stuff too.
            options['filter_expired'] = False

        keys = kind.all(**options).fetch(200)
        while keys:
            logging.info('%s: deleting %d...' % (kind.kind(), len(keys)))
            db.delete(keys)
            keys = kind.all(**options).fetch(200)

def reset_datastore():
    """Wipes everything in the datastore except Accounts and Secrets,
    then sets up the datastore for new data."""
    wipe_datastore()
    setup_datastore()

def setup_subdomains():
    Subdomain(key_name='haiti').put()
    Subdomain(key_name='chile').put()
    Subdomain(key_name='china').put()
    Subdomain(key_name='pakistan').put()
    Subdomain(key_name='lang-test').put()

def setup_configs():
    """Installs the configuration settings for Haiti, Chile, China, Pakistan."""
    COMMON_KEYWORDS = ['person', 'people', 'finder', 'person finder',
                       'people finder', 'crisis', 'survivor', 'family']

    # NOTE: the following two CAPTCHA keys are dummy keys for testing only. They
    # should be replaced with secret keys upon launch.
    config.set(captcha_private_key='6LfiOr8SAAAAAFyxGzWkhjo_GRXxYoDEbNkt60F2',
               captcha_public_key='6LfiOr8SAAAAAM3wRtnLdgiVfud8uxCqVVJWCs-z')

    # Google Language API key registered for person-finder.appspot.com
    config.set(language_api_key='ABQIAAAAkyNXK1D6CLHJNPVQfiU8DhQowImlwyPaNDI' +
                                'ohCJwgv-5lcExKBTP5o1_bXlgQjGi0stsXRtN-p8fdw')

    config.set_for_subdomain(
        'haiti',
        # Appended to "Google Person Finder" in page titles.
        subdomain_titles={
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
        # If false, hide the last_name field and use only first_name.
        use_family_name=True,
        # Presentation order for the given name and family name.
        family_name_first=False,
        # If false, hide the home_zip field.
        use_postal_code=True,
        # Require at least this many letters in each word of a text query.
        min_query_word_length=2,
        # Default map viewport for the location field in the note form.
        map_default_zoom=7,
        map_default_center=[18.968637, -72.284546],
        map_size_pixels=[400, 280],
        # If true, the feeds and read API require an authorization key.
        read_auth_key_required=False,
        # If true, the search API requires an authorization key.
        search_auth_key_required=False
    )

    config.set_for_subdomain(
        'chile',
        subdomain_titles={
            'en': 'Chile Earthquake',
            'es': 'Terremoto en Chile'
        },
        language_menu_options=['en', 'es'],
        keywords=', '.join([
            'chile', 'earthquake', 'chile earthquake', 'chilean',
            'terremoto', 'terremoto de chile',
            'sobreviviente', 'buscador de personas'
        ] + COMMON_KEYWORDS),
        use_family_name=True,
        family_name_first=False,
        use_postal_code=True,
        min_query_word_length=2,
        map_default_zoom=6,
        map_default_center=[-35, -72],  # near Curico, Chile
        map_size_pixels=[400, 500],
        read_auth_key_required=False,
        search_auth_key_required=False   
    )

    config.set_for_subdomain(
        'china',
        subdomain_titles={
            'en': 'China Earthquake',
            'zh-TW': u'\u4e2d\u570b\u5730\u9707',
            'zh-CN': u'\u4e2d\u56fd\u5730\u9707'
        },
        language_menu_options=['en', 'zh-TW', 'zh-CN'],
        keywords=', '.join([
            'china', 'earthquake', 'china earthquake', 'chinese',
            'qinghai', 'yushu'] + COMMON_KEYWORDS),
        use_family_name=True,
        family_name_first=True,
        use_postal_code=True,
        min_query_word_length=1,
        map_default_zoom=7,
        map_default_center=[33.005822, 97.006636],  # near Yushu, China
        map_size_pixels=[400, 280],
        read_auth_key_required=False,
        search_auth_key_required=False   
 )

    config.set_for_subdomain(
        'pakistan',
        subdomain_titles={
            'en': 'Pakistan Floods',
            'ur': u'\u067e\u0627\u06a9\u0633\u062a\u0627\u0646\u06cc \u0633\u06cc\u0644\u0627\u0628'
        },
        language_menu_options=['en', 'ur'],
        keywords=', '.join([
            'pakistan', 'flood', 'pakistan flood', 'pakistani'
        ] + COMMON_KEYWORDS),
        use_family_name=False,
        family_name_first=False,
        use_postal_code=False,
        min_query_word_length=1,
        map_default_zoom=6,
        map_default_center=[33.36, 73.26],  # near Rawalpindi, Pakistan
        map_size_pixels=[400, 500],
        read_auth_key_required=False,
        search_auth_key_required=False   
    )

    config.set_for_subdomain(
        'lang-test',
        # We set empty titles to avoid going over the 500-char limit
        # of the field
        subdomain_titles=dict(zip(LANGUAGE_ENDONYMS.keys(),
                                  [''] * len(LANGUAGE_ENDONYMS))),
        language_menu_options=list(LANGUAGE_EXONYMS.keys()),
        keywords=', '.join(COMMON_KEYWORDS),
        use_family_name=True,
        family_name_first=True,
        use_postal_code=True,
        min_query_word_length=1,
        map_default_zoom=6,
        map_default_center=[0 ,0],
        map_size_pixels=[400, 500],
        read_auth_key_required=False,
        search_auth_key_required=False   
    )
