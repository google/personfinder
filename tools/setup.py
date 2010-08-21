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
    setup_configs()

def wipe_datastore(*kinds):
    """Deletes everything in the datastore except Accounts and Secrets.
    If 'kinds' is given, deletes only those kinds of entities."""
    for kind in kinds or [Person, Note, Photo, Authorization, Secret,
                          EntityCounter]:
        keys = kind.all(keys_only=True).fetch(200)
        while keys:
            logging.info('%s: deleting %d...' % (kind.kind(), len(keys)))
            db.delete(keys)
            keys = kind.all(keys_only=True).fetch(200)

def reset_datastore():
    """Wipes everything in the datastore except Accounts and Secrets,
    then sets up the datastore for new data."""
    wipe_datastore()
    setup_datastore()

def setup_configs():
    """Installs the configuration settings for Haiti, Chile, China, Pakistan."""
    COMMON_KEYWORDS = ['person', 'people', 'finder', 'person finder',
                       'people finder', 'crisis', 'survivor', 'family']

    config.set_for_subdomain(
        'haiti',
        # Appended to "Google Person Finder" in page titles.
        subdomain_title={'en': 'Haiti Earthquake'},
        # List of language codes that appear in the language menu.
        language_menu_options=['en', 'ht', 'fr', 'es'],
        # Content for the <meta name="keywords"> tag.
        keywords=', '.join([
            'haiti', 'earthquake', 'haiti earthquake', 'haitian',
            u'ha\xe4ti', u's\xe9isme', 'tremblement', 'tremblement de terre',
            'famille', 'recherche de personnes'
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
        map_size_pixels=[400, 280]
    )

    config.set_for_subdomain(
        'chile',
        subdomain_title={'en': 'Chile Earthquake'},
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
        map_size_pixels=[400, 500]
    )

    config.set_for_subdomain(
        'china',
        subdomain_title={'en': 'China Earthquake'},
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
        map_size_pixels=[400, 280]
    )

    config.set_for_subdomain(
        'pakistan',
        subdomain_title={'en': 'Pakistan Floods'},
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
        map_size_pixels=[400, 500]
    )
