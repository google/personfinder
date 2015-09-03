# This file is originally from recaptcha-client 1.0.5 (obtained from pypi),
# now modified to use new Recaptcha.

import urllib
import urllib2

import config
import simplejson

import logging
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
                     lang='en'):
    """Gets the HTML to display for reCAPTCHA

    public_key -- The public api key
    use_ssl -- Should the request be sent over ssl?
    error -- An error message to display (from RecaptchaResponse.error_code)"""

    error_param = ''
    if error:
        logging.info(error)
        error_param = '&error=%s' % error
    server = API_SERVER
    if use_ssl:
        server = API_SSL_SERVER

    html = '''
<script src='%(server)s.js?hl=%(lang)s'></script>
<noscript>
  <div>
    <iframe src="%(server)s/fallback?k=%(public_key)s" height="450" width="302" frameborder="3"></iframe>
  </div>
  <div>
    <textarea id="g-recaptcha-response" name="g-recaptcha-response"></textarea>
  </div>
</noscript>
''' % {
    'server': server,
    'lang': lang,
    'public_key': public_key,
}
    if error:
        return html + '''<div>error=%(error)s</div>'''%{'error':error}
    else:
        return html


def submit (recaptcha_response):
    """
    Submits a reCAPTCHA request for verification. Returns RecaptchaResponse
    for the request

    recaptcha_response -- The value of recaptcha_response
    """

    if not (recaptcha_response and len(recaptcha_response)):
        return RecaptchaResponse (is_valid=False, error_code='incorrect-captcha-sol')

    secret_key = config.get('captcha_secret_key')
    request_url = (
        "https://www.google.com/recaptcha/api/siteverify?secret=%s&response=%s"
        % (secret_key, recaptcha_response))
    recaptcha_request = urllib2.Request (request_url)
    response = urllib2.urlopen (recaptcha_request)
    result = simplejson.load(response)
    result_code = result['success']
    if result_code:
        return RecaptchaResponse (is_valid=True)
    else:
        return RecaptchaResponse (is_valid=False, error_code=result['error-codes'][0])
