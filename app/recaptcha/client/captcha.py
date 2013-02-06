# This file is originally from recaptcha-client 1.0.5 (obtained from pypi),
# now modified to support custom translations.

import urllib
import urllib2

import simplejson

API_SSL_SERVER = 'https://www.google.com/recaptcha/api'
# We leave out the URL scheme so that browsers won't complain when accessed
# from a secure website even when use_ssl is not set.
API_SERVER = '//www.google.com/recaptcha/api'
VERIFY_SERVER = 'api-verify.recaptcha.net'

class RecaptchaResponse(object):
    def __init__(self, is_valid, error_code=None):
        self.is_valid = is_valid
        self.error_code = error_code

def get_display_html(public_key, use_ssl=False, error=None,
                     lang='en', custom_translations={}):
    """Gets the HTML to display for reCAPTCHA

    public_key -- The public api key
    use_ssl -- Should the request be sent over ssl?
    error -- An error message to display (from RecaptchaResponse.error_code)"""

    error_param = ''
    if error:
        error_param = '&error=%s' % error
    server = API_SERVER
    if use_ssl:
        server = API_SSL_SERVER

    # _('...') used to return objects that are unpalatable to simplejson.
    # For better compatibility, we keep this conversion code, but execute it
    # only when values are non-unicode to prevent UnicodeEncodeError.
    if any(not isinstance(v, unicode) for v in custom_translations.values()):
      custom_translations = dict((k, unicode(str(v), 'utf-8'))
                                 for (k, v) in custom_translations.items())

    options = {
        'theme': 'white',
        'lang': lang,
        'custom_translations': custom_translations
    }

    return '''
<script>
  var RecaptchaOptions = %(options)s;
</script>
<script src="%(server)s/challenge?k=%(public_key)s%(error_param)s"></script>

<noscript>
  <iframe src="%(server)s/noscript?k=%(public_key)s%(error_param)s"
      height="300" width="500" frameborder="0"></iframe><br>
  <textarea name="recaptcha_challenge_field" rows="3" cols="40"></textarea>
  <input type="hidden" name="recaptcha_response_field" value="manual_challenge">
</noscript>
''' % {
    'options': simplejson.dumps(options),
    'server': server,
    'public_key': public_key,
    'error_param': error_param,
}


def submit (recaptcha_challenge_field,
            recaptcha_response_field,
            private_key,
            remoteip):
    """
    Submits a reCAPTCHA request for verification. Returns RecaptchaResponse
    for the request

    recaptcha_challenge_field -- The value of recaptcha_challenge_field from the form
    recaptcha_response_field -- The value of recaptcha_response_field from the form
    private_key -- your reCAPTCHA private key
    remoteip -- the user's ip address
    """

    if not (recaptcha_response_field and recaptcha_challenge_field and
            len (recaptcha_response_field) and len (recaptcha_challenge_field)):
        return RecaptchaResponse (is_valid = False, error_code = 'incorrect-captcha-sol')
    

    def encode_if_necessary(s):
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s

    params = urllib.urlencode ({
            'privatekey': encode_if_necessary(private_key),
            'remoteip' :  encode_if_necessary(remoteip),
            'challenge':  encode_if_necessary(recaptcha_challenge_field),
            'response' :  encode_if_necessary(recaptcha_response_field),
            })

    request = urllib2.Request (
        url = "http://%s/verify" % VERIFY_SERVER,
        data = params,
        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "User-agent": "reCAPTCHA Python"
            }
        )
    
    httpresp = urllib2.urlopen (request)

    return_values = httpresp.read ().splitlines ();
    httpresp.close();

    return_code = return_values [0]

    if (return_code == "true"):
        return RecaptchaResponse (is_valid=True)
    else:
        return RecaptchaResponse (is_valid=False, error_code = return_values [1])
