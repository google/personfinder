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
HOME_DOMAIN = 'google.com'

# TODO(shakusa) Make this configurable via a command-line flag

# List of languages that appear in the language menu, as (code, name) pairs.
LANGUAGES = [('ar', u'\u0627\u0644\u0639\u0631\u0628\u064A'), # Arabic
             ('bg', u'\u0431\u044A\u043B\u0433\u0430\u0440\u0441\u043A\u0438'), # Bulgarian
             ('ca', u'Catal\u00E0'), # Catalan
             ('cs', u'\u010De\u0161tina'), # Czech
             ('da', 'Dansk'), # Danish
             ('el', u'\u0395\u03BB\u03BB\u03B7\u03BD\u03B9\u03BA\u03AC'), # Greek
             ('en', 'English'),
             ('en_GB', 'English (UK)'),
             ('es', u'Espa\u00F1ol'), # Spanish
             ('eu', 'euskara'), # Basque
             ('fa', u'\u0641\u0627\u0631\u0633\u06CC'), # Persian
             ('fi', 'suomi'), # Finnish
             ('fil', 'Filipino'),
             ('fr', u'Fran\u00e7ais'), # French
             ('fr_CA', u'Fran\u00e7ais (Canada)'), # Canadian French
             ('gl', 'Galego'), # Galician
             ('hi', u'\u0939\u093F\u0928\u094D\u0926\u0940'), # Hindi
             ('hr', 'Hrvatski'), # Croatian
             ('ht', u'Krey\u00f2l'), # Kreyol
             ('hu', 'magyar'), # Hungarian
             ('id', 'Bahasa Indonesia'), # Indonesian
             ('he', u'\u05E2\u05D1\u05E8\u05D9\u05EA'), # Hebrew
             ('ja', u'\u65E5\u672C\u8A9E'), # Japanese
             ('ko', u'\uD55C\uAD6D\uC5B4'), # Korean
             ('lt', u'Latvie\u0161u valoda'), # Latvian
             ('nl', 'Nederlands'), # Dutch
             ('no', 'Norsk'), # Norwegian
             ('pl', 'polski'), # Polish
             ('pt_PT', u'Portugu\u00EAs'), # Portuguese (Portugal)
             ('ro', u'Rom\u00E2n\u0103'), # Romanian
             ('ru', u'\u0420\u0443\u0441\u0441\u043A\u0438\u0439'), # Russian
             ('sk', u'Sloven\u010Dina'), # Slovak
             ('sl', u'Sloven\u0161\u010Dina'), # Slovenian
             ('sr', u'\u0441\u0440\u043F\u0441\u043A\u0438'), # Serbian
             ('sv', 'Svenska'), # Swedish
             ('th', u'\u0E44\u0E17\u0E22'), # Thai
             ('tr', u'T\u00FCrk\u00E7e'), # Turkish
             ('uk', u'\u0423\u043A\u0440\u0430\u0457\u043D\u0441\u044C\u043A\u0430'), # Ukranian
             ('vi', u'Ti\u1EBFng Vi\u1EC7t'), # Vietnamese
             ('zh_TW', u'\u4E2D \u6587 (\u7E41 \u9AD4)'), # Chinese (Traditional)
             ('zh_CN', u'\u4E2D \u6587 (\u7B80 \u4F53)') # Chinese (Simplified)
             ]

# Content for the <meta name="keywords"> tag.
KEYWORDS = u'haiti, earthquake, people, person, finder, person finder, people finder, haiti earthquake, haitian, crisis, survivor, family, s\xe9isme, ha\xe4ti, tremblement, tremblement de terre, famille, recherche de personnes'

# Appended to "Google Person Finder" in page titles.
# TODO(kpy): Localize this dynamic parameter.
SUBTITLE = 'Haiti Earthquake'
