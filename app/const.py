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

"""Constants that aren't specific to a particular module or handler."""

# We use lazy translation in this file because the language isn't set yet.
import django_setup
from django_setup import gettext_lazy as _

# The root URL of this application.
ROOT_URL = 'http://google.org/personfinder'

# The domain name of this application.  The application hosts multiple
# repositories; each repository ID is http://<HOME_DOMAIN>/<REPO>.
HOME_DOMAIN = 'personfinder.google.org'

# Mapping from language codes to endonyms for all available languages.
# You can get the list of language names in each language in Unicode CLDR data.
# Go to http://unicode.org/Public/cldr/latest , download core.zip and look
# at common/main/*.xml in it.
# Some names are taken from Wikipedia because they are missing in CLDR data or
# they are in different script from our translation.
LANGUAGE_ENDONYMS = {
    'af': u'Afrikaans',
    'am': u'\u12a0\u121b\u122d\u129b',
    'ar': u'\u0627\u0644\u0639\u0631\u0628\u064A\u0629',
    'az': u'az\u0259rbaycanca',
    'bg': u'\u0431\u044A\u043B\u0433\u0430\u0440\u0441\u043A\u0438',
    'bn': u'\u09ac\u09be\u0982\u09b2\u09be',
    'ca': u'Catal\u00E0',
    'cs': u'\u010De\u0161tina',
    'da': u'Dansk',
    'de': u'Deutsch',
    'el': u'\u0395\u03BB\u03BB\u03B7\u03BD\u03B9\u03BA\u03AC',
    'en': u'English',
    'en-GB': u'English (UK)',
    'es': u'espa\u00F1ol',
    'es-419': u'espa\u00F1ol (Latinoam\u00e9rica)',
    'et': u'eesti',
    'eu': u'Euskara',
    'fa': u'\u0641\u0627\u0631\u0633\u06CC',
    'fi': u'suomi',
    'fil': u'Filipino',
    'fr': u'Fran\u00e7ais',
    'fr-CA': u'Fran\u00e7ais (Canada)',
    'gl': u'Galego',
    'gu': u'\u0a97\u0ac1\u0a9c\u0ab0\u0abe\u0aa4\u0ac0',
    'hi': u'\u0939\u093F\u0928\u094D\u0926\u0940',
    'hr': u'Hrvatski',
    'ht': u'Krey\u00f2l',
    'hu': u'magyar',
    'hy': u'\u0570\u0561\u0575\u0565\u0580\u0565\u0576',
    'id': u'Bahasa Indonesia',
    'is': u'\u00edslenska',
    'it': u'Italiano',
    'iw': u'\u05E2\u05D1\u05E8\u05D9\u05EA',
    'ja': u'\u65E5\u672C\u8A9E',
    'jv': u'basa Jawa',
    'ka': u'\u10e5\u10d0\u10e0\u10d7\u10e3\u10da\u10d8',
    'kk': u'\u049b\u0430\u0437\u0430\u049b \u0442\u0456\u043b\u0456',
    'km': u'\u1781\u17d2\u1798\u17c2\u179a',
    'kn': u'\u0c95\u0ca8\u0ccd\u0ca8\u0ca1',
    'ko': u'\uD55C\uAD6D\uC5B4',
    'ky': u'\u041a\u044b\u0440\u0433\u044b\u0437',
    'lo': u'\u0ea5\u0eb2\u0ea7',
    'lt': u'Lietuvi\u0173',
    'lv': u'Latvie\u0161u valoda',
    'mk': u'\u043c\u0430\u043a\u0435\u0434\u043e\u043d\u0441\u043a\u0438',
    'ml': u'\u0d2e\u0d32\u0d2f\u0d3e\u0d33\u0d02',
    'mn': u'\u043c\u043e\u043d\u0433\u043e\u043b',
    'mr': u'\u092e\u0930\u093e\u0920\u0940',
    'ms': u'Bahasa Melayu',
    'my': u'\u1017\u1019\u102c',
    'ne': u'\u0928\u0947\u092a\u093e\u0932\u0940',
    'nl': u'Nederlands',
    'no': u'Norsk',
    'pa': u'\u0a2a\u0a70\u0a1c\u0a3e\u0a2c\u0a40',
    'pl': u'polski',
    'prs': u'\u062F\u0631\u06CC',
    'ps': u'\u067E\u069A\u062A\u0648',
    'pt-BR': u'Portugu\u00EAs (Brasil)',
    'pt-PT': u'Portugu\u00EAs (Portugal)',
    'ro': u'Rom\u00E2n\u0103',
    'ru': u'\u0420\u0443\u0441\u0441\u043A\u0438\u0439',
    'si': u'\u0dc3\u0dd2\u0d82\u0dc4\u0dbd',
    'sk': u'Sloven\u010Dina',
    'sl': u'Sloven\u0161\u010Dina',
    'sq': u'shqip',
    'sr': u'\u0441\u0440\u043F\u0441\u043A\u0438',
    'su': u'Basa Sunda',
    'sv': u'Svenska',
    'sw': u'Kiswahili',
    'ta': u'\u0ba4\u0bae\u0bbf\u0bb4\u0bcd',
    'te': u'\u0c24\u0c46\u0c32\u0c41\u0c17\u0c41',
    'th': u'\u0E44\u0E17\u0E22',
    'tr': u'T\u00FCrk\u00E7e',
    'uk': u'\u0423\u043A\u0440\u0430\u0457\u043D\u0441\u044C\u043A\u0430',
    'ur': u'\u0627\u0631\u062F\u0648',
    'uz': u'o\u02bbzbek tili',
    'vi': u'Ti\u1EBFng Vi\u1EC7t',
    'zh-CN': u'\u4E2D \u6587 (\u7B80 \u4F53)',
    'zh-HK': u'\u4E2D \u6587 (\u9999 \u6e2f)',
    'zh-TW': u'\u4E2D \u6587 (\u7E41 \u9AD4)',
    'zu': u'isiZulu',
}

# Mapping from language codes to English names for all available languages.
# You can get the list of language names in each language in Unicode CLDR data.
# Go to http://unicode.org/Public/cldr/latest , download core.zip and look
# at common/main/*.xml in it.
LANGUAGE_EXONYMS = {
    'af': 'Afrikaans',
    'am': 'Amharic',
    'ar': 'Arabic',
    'az': 'Azerbaijani',
    'bg': 'Bulgarian',
    'bn': 'Bengali',
    'ca': 'Catalan',
    'cs': 'Czech',
    'da': 'Danish',
    'de': 'German',
    'el': 'Greek',
    'en': 'English (US)',
    'en-GB': 'English (UK)',
    'es': 'Spanish',
    'es-419': 'Spanish (Latin America)',
    'et': 'Estonian',
    'eu': 'Basque',
    'fa': 'Persian',
    'fi': 'Finnish',
    'fil': 'Filipino',
    'fr': 'French (France)',
    'fr-CA': 'French (Canada)',
    'gl': 'Galician',
    'gu': 'Gujarati',
    'hi': 'Hindi',
    'hr': 'Croatian',
    'ht': 'Haitian Creole',
    'hu': 'Hungarian',
    'hy': 'Armenian',
    'id': 'Indonesian',
    'is': 'Icelandic',
    'it': 'Italian',
    'iw': 'Hebrew',
    'ja': 'Japanese',
    'jv': 'Javanese',
    'ka': 'Georgian',
    'kk': 'Kazakh',
    'km': 'Khmer',
    'kn': 'Kannada',
    'ko': 'Korean',
    'ky': 'Kirghiz',
    'lo': 'Lao',
    'lt': 'Lithuanian',
    'lv': 'Latvian',
    'mk': 'Macedonian',
    'ml': 'Malayalam',
    'mn': 'Mongolian',
    'mr': 'Marathi',
    'ms': 'Malay',
    'my': 'Burmese',
    'ne': 'Nepali',
    'nl': 'Dutch',
    'no': 'Norwegian',
    'pa': 'Punjabi',
    'pl': 'Polish',
    'prs': 'Dari',
    'ps': 'Pashto',
    'pt-BR': 'Portuguese (Brazil)',
    'pt-PT': 'Portuguese (Portugal)',
    'ro': 'Romanian',
    'ru': 'Russian',
    'si': 'Sinhala',
    'sk': 'Slovak',
    'sl': 'Slovenian',
    'sq': 'Albanian',
    'sr': 'Serbian',
    'su': 'Sundanese',
    'sv': 'Swedish',
    'sw': 'Swahili',
    'ta': 'Tamil',
    'te': 'Telugu',
    'th': 'Thai',
    'tr': 'Turkish',
    'uk': 'Ukranian',
    'ur': 'Urdu',
    'uz': 'Uzbek',
    'vi': 'Vietnamese',
    'zh-CN': 'Chinese (Simplified)',
    'zh-HK': 'Chinese (Hong Kong)',
    'zh-TW': 'Chinese (Traditional)',
    'zu': 'Zulu',
}

# See go/iii
LANGUAGE_SYNONYMS = {
    'he' : 'iw',
    'in' : 'id',
    'mo' : 'ro',
    # Note that we don't currently support jv (Javanese) or yi (Yiddish).
    'jw' : 'jv',
    'ji' : 'yi',
    # Django has a bug that django.utils.translation.activate() throws
    # AttributeError when:
    # - The language is not in $APPENGINE_DIR/lib/django_1_2/django/conf/locale
    # - The language code contains a dash '-'
    # and 'zh-HK' meets both criteria. We workaround this bug by using 'zhhk'
    # instead of 'zh-HK' internally.
    #
    # The cause of the bug is that
    # $APPENGINE_DIR/lib/django_1_2/django/utils/translation/trans_real.py:142
    # accesses res._info even when res is None.
    'zh-HK': 'zhhk',
}

# RTL languages.
LANGUAGES_BIDI = django_setup.LANGUAGES_BIDI + ['ps', 'prs']

# Mapping from language codes to the names of LayoutCode constants.  See:
# http://code.google.com/apis/ajaxlanguage/documentation/referenceKeyboard.html
VIRTUAL_KEYBOARD_LAYOUTS = {
    'ur': 'URDU'
}

# Charset string for UTF-8 used in env.charset.
CHARSET_UTF8 = 'utf-8'

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

# The list of external websites with profile pages sorted in the order they are
# shown in create page, used as the default value for profile_websites config.
DEFAULT_PROFILE_WEBSITES = [
    {
        # Display name of the website
        'name': 'Facebook',
        # Filename of the icon file served as /global/<icon_filename>.
        'icon_filename': 'facebook-16x16.png',
        # Regexp to check for valid profile page URLs.
        'url_regexp': 'https?://(www\\.)?facebook\\.com/.*',
    },
    {
        'name': 'Twitter',
        'icon_filename': 'twitter-16x16.png',
        'url_regexp': 'https?://(www\\.)?twitter\\.com/.*',
    },
    {
        'name': 'LinkedIn',
        'icon_filename': 'linkedin-16x16.png',
        'url_regexp': 'https?://(www\\.)?linkedin\\.com/.*',
    },
]

# Default values used in the notification process which sends emails to notify
# bad status in repositories. The notification process will run every 6 hours
# by default and you can change this interval by editing app/cron.yaml.

# The email address which is used in the notification process.
DEFAULT_NOTIFICATION_EMAIL = ''
# The threshold for the number of unreviewed notes. If the number of unreviewed
# notes exceeds this threshold, notification process will notify it by an email.
DEFAULT_UNREVIEWED_NOTES_THRESHOLD = 100
