# This file is originally from recaptcha-client 1.0.5 (obtained from pypi),
# now modified to use new Recaptcha.

import urllib
import urllib2

import config
import simplejson

from django.utils.html import escape

API_SSL_SERVER = 'https://www.google.com/recaptcha/api'
# We leave out the URL scheme so that browsers won't complain when accessed
# from a secure website even when use_ssl is not set.
API_SERVER = '//www.google.com/recaptcha/api'
VERIFY_SERVER = 'api-verify.recaptcha.net'

class RecaptchaResponse(object):
    def __init__(self, is_valid, error_code=None):
        self.is_valid = is_valid
        self.error_code = error_code

def get_display_html(site_key, use_ssl=False, error=None,
                     lang='en'):
    """Gets the HTML to display for reCAPTCHA

    site_key -- The public api key
    use_ssl -- Should the request be sent over ssl?
    error -- An error message to display (from RecaptchaResponse.error_code)"""

    server = API_SERVER
    if use_ssl:
        server = API_SSL_SERVER

    html = '''
<script src='%(server)s.js?hl=%(lang)s'></script>
<div class='g-recaptcha' data-sitekey='%(site_key)s'></div>
<noscript>
  <div style='width: 302px; height: 422px;'>
    <div style='width: 302px; height: 422px; position: relative;'>
      <div style='width: 302px; height: 422px; position: absolute;'>
        <iframe src='%(server)s/fallback?k=%(site_key)s'
                frameborder="0" scrolling="no"
                style='width: 302px; height:422px; border-style: none;'>
        </iframe>
      </div>

    </div>
      <div style='width: 300px; height: 60px; border-style: none;
                  bottom: 12px; left: 25px; margin: 0px; padding: 0px; right: 25px;
                  background: #f9f9f9; border: 1px solid #c1c1c1; border-radius: 3px;'>
        <textarea id="g-recaptcha-response" name="g-recaptcha-response"
                  class="g-recaptcha-response"
                  style="width: 250px; height: 40px; border: 1px solid #c1c1c1;
                         margin: 10px 25px; padding: 0px; resize: none;">
        </textarea>
      </div>
  </div>
</noscript><br/><br/><br/>
''' % {
    'server': server,
    'lang': lang,
    'site_key': site_key,
}
    if error:
        return "<div>%(error)s</div>" % {'error': escape(error)} + html
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
        error_codes = result.get('error-codes')
        # It seems 'error-codes' attribute is sometimes missing.
        error_code = error_codes[0] if error_codes else 'unknown-error'
        return RecaptchaResponse (is_valid=False, error_code=error_code)
