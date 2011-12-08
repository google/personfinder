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

"""Constants that aren't specific to a particular module or handler."""

# We use lazy translation in this file because the language isn't set yet.
from i18n_setup import gettext_lazy as _

# Mapping from language codes to endonyms for all available languages.
LANGUAGE_ENDONYMS = {
    'ar': u'\u0627\u0644\u0639\u0631\u0628\u064A\u0629',
    'bg': u'\u0431\u044A\u043B\u0433\u0430\u0440\u0441\u043A\u0438',
    'ca': u'Catal\u00E0',
    'cs': u'\u010De\u0161tina',
    'da': u'Dansk',
    'de': u'Deutsch',
    'el': u'\u0395\u03BB\u03BB\u03B7\u03BD\u03B9\u03BA\u03AC',
    'en': u'English',
    'en-GB': u'English (UK)',
    'es': u'espa\u00F1ol',
    'es_419': u'espa\u00F1ol (Latinoam\u00e9rica)',
    'eu': u'Euskara',
    'fa': u'\u0641\u0627\u0631\u0633\u06CC',
    'fi': u'suomi',
    'fil': u'Filipino',
    'fr': u'Fran\u00e7ais',
    'fr-CA': u'Fran\u00e7ais (Canada)',
    'gl': u'Galego',
    'hi': u'\u0939\u093F\u0928\u094D\u0926\u0940',
    'hr': u'Hrvatski',
    'ht': u'Krey\u00f2l',
    'hu': u'magyar',
    'id': u'Bahasa Indonesia',
    'it': u'Italiano',
    'he': u'\u05E2\u05D1\u05E8\u05D9\u05EA',
    'ja': u'\u65E5\u672C\u8A9E',
    'ko': u'\uD55C\uAD6D\uC5B4',
    'lt': u'Lietuvi\u0173',
    'lv': u'Latvie\u0161u valoda',
    'nl': u'Nederlands',
    'no': u'Norsk',
    'pl': u'polski',
    'pt-PT': u'Portugu\u00EAs (Portugal)',
    'pt-BR': u'Portugu\u00EAs (Brasil)',
    'ro': u'Rom\u00E2n\u0103',
    'ru': u'\u0420\u0443\u0441\u0441\u043A\u0438\u0439',
    'sk': u'Sloven\u010Dina',
    'sl': u'Sloven\u0161\u010Dina',
    'sr': u'\u0441\u0440\u043F\u0441\u043A\u0438',
    'sv': u'Svenska',
    'th': u'\u0E44\u0E17\u0E22',
    'tr': u'T\u00FCrk\u00E7e',
    'uk': u'\u0423\u043A\u0440\u0430\u0457\u043D\u0441\u044C\u043A\u0430',
    'ur': u'\u0627\u0631\u062F\u0648',
    'vi': u'Ti\u1EBFng Vi\u1EC7t',
    'zh-TW': u'\u4E2D \u6587 (\u7E41 \u9AD4)',
    'zh-CN': u'\u4E2D \u6587 (\u7B80 \u4F53)',
}

# Mapping from language codes to English names for all available languages.
LANGUAGE_EXONYMS = {
    'ar': 'Arabic',
    'bg': 'Bulgarian',
    'ca': 'Catalan',
    'cs': 'Czech',
    'da': 'Danish',
    'de': 'German',
    'el': 'Greek',
    'en': 'English (US)',
    'en-GB': 'English (UK)',
    'es': 'Spanish',
    'es_419': 'Spanish (Latin America)',
    'eu': 'Basque',
    'fa': 'Persian',
    'fi': 'Finnish',
    'fil': 'Filipino',
    'fr': 'French (France)',
    'fr-CA': 'French (Canada)',
    'gl': 'Galician',
    'hi': 'Hindi',
    'hr': 'Croatian',
    'ht': 'Haitian Creole',
    'hu': 'Hungarian',
    'id': 'Indonesian',
    'it': 'Italian',
    'he': 'Hebrew',
    'ja': 'Japanese',
    'ko': 'Korean',
    'lt': 'Lithuanian',
    'lv': 'Latvian',
    'nl': 'Dutch',
    'no': 'Norwegian',
    'pl': 'Polish',
    'pt-PT': 'Portuguese (Portugal)',
    'pt-BR': 'Portuguese (Brazil)',
    'ro': 'Romanian',
    'ru': 'Russian',
    'sk': 'Slovak',
    'sl': 'Slovenian',
    'sr': 'Serbian',
    'sv': 'Swedish',
    'th': 'Thai',
    'tr': 'Turkish',
    'uk': 'Ukranian',
    'ur': 'Urdu',
    'vi': 'Vietnamese',
    'zh-TW': 'Chinese (Traditional)',
    'zh-CN': 'Chinese (Simplified)',
}

# Mapping from language codes to the names of LayoutCode constants.  See:
# http://code.google.com/apis/ajaxlanguage/documentation/referenceKeyboard.html
VIRTUAL_KEYBOARD_LAYOUTS = {
    'ur': 'URDU'
}

# UI text for the sex field when displaying a person.
PERSON_SEX_TEXT = {
    # This dictionary must have an entry for '' that gives the default text.
    '': '',
    'female': _('female'),
    'male': _('male'),
    'other': _('other')
}

# UI text for the expiry field when displayinga person.
PERSON_EXPIRY_TEXT = {
    '30': _('About 1 month (30 days) from now'),
    '60': _('About 2 months (60 days) from now'),
    '90': _('About 3 months (90 days) from now'),
    '180': _('About 6 months (180 days) from now'),
    '360': _('About 1 year (360 days) from now'),
}

# UI text for the status field when posting or displaying a note.
NOTE_STATUS_TEXT = {
    # This dictionary must have an entry for '' that gives the default text.
    '': _('Unspecified'),
    'information_sought': _('I am seeking information'),
    'is_note_author': _('I am this person'),
    'believed_alive':
        _('I have received information that this person is alive'),
    'believed_missing': _('I have reason to think this person is missing'),
    'believed_dead': _('I have received information that this person is dead'),
}

# UI text for the rolled-up status when displaying a person.
PERSON_STATUS_TEXT = {
    # This dictionary must have an entry for '' that gives the default text.
    '': _('Unspecified'),
    'information_sought': _('Someone is seeking information about this person'),
    'is_note_author': _('This person has posted a message'),
    'believed_alive':
        _('Someone has received information that this person is alive'),
    'believed_missing': _('Someone has reported that this person is missing'),
    'believed_dead':
        _('Someone has received information that this person is dead'),
}
