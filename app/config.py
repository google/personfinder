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

# Application-wide configuration settings.

# Home domain of the PFIF repository.  This should match the hostname where
# the application is hosted.
HOME_DOMAIN = 'haiticrisis.appspot.com'

# TODO(shakusa): Make this configurable.
# List of language codes that appear in the language menu.
LANGUAGE_MENU_OPTIONS = ['en', 'ht', 'fr', 'es', 'ur']

# Mapping from language codes to endonyms for all available languages.
LANGUAGE_ENDONYMS = {
    'ar': u'\u0627\u0644\u0639\u0631\u0628\u064A\u0629',  # Arabic
    'bg':  # Bulgarian
        u'\u0431\u044A\u043B\u0433\u0430\u0440\u0441\u043A\u0438',
    'ca': u'Catal\u00E0',  # Catalan
    'cs': u'\u010De\u0161tina',  # Czech
    'da': u'Dansk',  # Danish
    'el': u'\u0395\u03BB\u03BB\u03B7\u03BD\u03B9\u03BA\u03AC',  # Greek
    'en': u'English',  # English
    'en-GB': u'English (UK)',
    'es': u'Espa\u00F1ol',  # Spanish
    'eu': u'euskara',  # Basque
    'fa': u'\u0641\u0627\u0631\u0633\u06CC',  # Persian
    'fi': u'suomi',  # Finnish
    'fil': u'Filipino',  # Filipino
    'fr': u'Fran\u00e7ais',  # French
    'fr-CA': u'Fran\u00e7ais (Canada)',  # Canadian French
    'gl': u'Galego',  # Galician
    'hi': u'\u0939\u093F\u0928\u094D\u0926\u0940',  # Hindi
    'hr': u'Hrvatski',  # Croatian
    'ht': u'Krey\u00f2l',  # Kreyol
    'hu': u'magyar',  # Hungarian
    'id': u'Bahasa Indonesia',  # Indonesian
    'he': u'\u05E2\u05D1\u05E8\u05D9\u05EA',  # Hebrew
    'ja': u'\u65E5\u672C\u8A9E',  # Japanese
    'ko': u'\uD55C\uAD6D\uC5B4',  # Korean
    'lt': u'Latvie\u0161u valoda',  # Latvian
    'nl': u'Nederlands',  # Dutch
    'no': u'Norsk',  # Norwegian
    'pl': u'polski',  # Polish
    'pt-PT': u'Portugu\u00EAs',  # Portuguese (Portugal)
    'ro': u'Rom\u00E2n\u0103',  # Romanian
    'ru': u'\u0420\u0443\u0441\u0441\u043A\u0438\u0439',  # Russian
    'sk': u'Sloven\u010Dina',  # Slovak
    'sl': u'Sloven\u0161\u010Dina',  # Slovenian
    'sr': u'\u0441\u0440\u043F\u0441\u043A\u0438',  # Serbian
    'sv': u'Svenska',  # Swedish
    'th': u'\u0E44\u0E17\u0E22',  # Thai
    'tr': u'T\u00FCrk\u00E7e',  # Turkish
    'uk':  # Ukranian
        u'\u0423\u043A\u0440\u0430\u0457\u043D\u0441\u044C\u043A\u0430',
    'ur': u'\u0627\u0631\u062F\u0648',  # Urdu
    'vi': u'Ti\u1EBFng Vi\u1EC7t',  # Vietnamese
    'zh-TW': u'\u4E2D \u6587 (\u7E41 \u9AD4)',  # Chinese (Traditional)
    'zh-CN': u'\u4E2D \u6587 (\u7B80 \u4F53)',  # Chinese (Simplified)
}

# Content for the <meta name="keywords"> tag.
KEYWORDS = u'haiti, earthquake, people, person, finder, person finder, people finder, haiti earthquake, haitian, crisis, survivor, family, s\xe9isme, ha\xe4ti, tremblement, tremblement de terre, famille, recherche de personnes'

# Appended to "Google Person Finder" in page titles.
# TODO(kpy): Localize this dynamic parameter.
SUBDOMAIN_TITLE = 'Haiti Earthquake'

# Presentation order for the given name and family name.
FAMILY_NAME_FIRST = False

# If false, hide the last_name field and use only first_name.
USE_FAMILY_NAME = True

# If false, hide the home_postal_code field.
USE_POSTAL_CODE = True

# Require at least this many letters in each word of a text query.
MIN_QUERY_WORD_LENGTH = 2

# Default map viewport for the form's location field.
MAP_DEFAULT_ZOOM = 7
MAP_DEFAULT_CENTER = (18.968637, -72.284546)
MAP_SIZE_PIXELS = (400, 280)

# Mapping from language codes to the names of LayoutCode constants.  See:
# http://code.google.com/apis/ajaxlanguage/documentation/referenceKeyboard.html
VIRTUAL_KEYBOARD_LAYOUTS = {
    'ur': 'URDU'
}

if False:  # settings for Chile
  HOME_DOMAIN = 'chilepersonfinder.appspot.com'
  LANGUAGE_MENU_OPTIONS = ['en', 'es']
  KEYWORDS = ('chile, earthquake, people, person, finder, person finder, ' +
              'people finder, chile earthquake, chilean, crisis, ' +
              'buscador de personas, terremoto de chile, sobreviviente')
  SUBDOMAIN_TITLE = 'Chile Earthquake'
  FAMILY_NAME_FIRST = False
  USE_FAMILY_NAME = True
  USE_POSTAL_CODE = True
  MIN_QUERY_WORD_LENGTH = 2
  MAP_DEFAULT_ZOOM = 6
  MAP_DEFAULT_CENTER = (-35, -72)  # near Curico, Chile
  MAP_SIZE_PIXELS = (400, 500)

if False:  # settings for China
  HOME_DOMAIN = 'chinapersonfinder.appspot.com'
  LANGUAGE_MENU_OPTIONS = ['en', 'zh-TW', 'zh-CN']
  KEYWORDS = ('china, earthquake, people, person, finder, person finder, ' +
              'people finder, china earthquake, chinese, qinghai, yushu')
  SUBDOMAIN_TITLE = 'China Earthquake'
  FAMILY_NAME_FIRST = True
  USE_FAMILY_NAME = True
  USE_POSTAL_CODE = True
  MIN_QUERY_WORD_LENGTH = 1
  MAP_DEFAULT_ZOOM = 7
  MAP_DEFAULT_CENTER = (33.0058220, 97.0066360)
  MAP_SIZE_PIXELS = (400, 280)

if False:  # settings for Pakistan
  HOME_DOMAIN = 'pakistan.person-finder.appspot.com'
  LANGUAGE_MENU_OPTIONS = ['en', 'ur']
  KEYWORDS = ('pakistan, flood, people, person, finder, person finder, ' +
              'people finder, pakistan floods, pakistani, crisis')
  SUBDOMAIN_TITLE = 'Pakistan Floods'
  FAMILY_NAME_FIRST = False
  USE_FAMILY_NAME = False
  USE_POSTAL_CODE = False
  MIN_QUERY_WORD_LENGTH = 1
  MAP_DEFAULT_ZOOM = 6
  MAP_DEFAULT_CENTER = (33.36, 73.26)  # near Rawalpindi, Pakistan
  MAP_SIZE_PIXELS = (400, 500)

