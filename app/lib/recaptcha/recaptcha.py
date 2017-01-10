################################################################################
#
# Copyright (c) 2012, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of python-recaptcha <http://packages.python.org/recaptcha>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
################################################################################
"""reCAPTCHA client."""

from json import dumps as json_encode
from urllib import urlencode
from urllib2 import Request
from urllib2 import URLError
from urllib2 import urlopen
from urlparse import urljoin
from urlparse import urlsplit
from urlparse import urlunsplit


__all__ = [
    'RECAPTCHA_CHARACTER_ENCODING',
    'RecaptchaClient',
    'RecaptchaException',
    'RecaptchaInvalidChallengeError',
    'RecaptchaInvalidPrivateKeyError',
    'RecaptchaUnreachableError'
    ]


_RECAPTCHA_API_URL = 'http://www.google.com/recaptcha/api/'


_RECAPTCHA_VERIFICATION_RELATIVE_URL_PATH = 'verify'
_RECAPTCHA_JAVASCRIPT_CHALLENGE_RELATIVE_URL_PATH = 'challenge'
_RECAPTCHA_NOSCRIPT_CHALLENGE_RELATIVE_URL_PATH = 'noscript'


RECAPTCHA_CHARACTER_ENCODING = 'UTF-8'
"""
The character encoding to be used when making requests to the remote API.

**Keep in mind that an ASCII string is also a valid UTF-8 string.** So
applications which use ASCII exclusively don't need to encode their strings to
use this library.

This is not officially documented but can be inferred from the encoding used in
the noscript challenge.

"""


_RECAPTCHA_CHALLENGE_MARKUP_TEMPLATE = """
<script type="text/javascript">
    var RecaptchaOptions = {recaptcha_options_json};
</script>
<script
    type="text/javascript"
    src="{javascript_challenge_url}"
    >
</script>
<noscript>
   <iframe
       src="{noscript_challenge_url}"
       height="300"
       width="500"
       frameborder="0"
       >
   </iframe>
   <br />
   <textarea name="recaptcha_challenge_field" rows="3" cols="40"></textarea>
   <input
       type="hidden"
       name="recaptcha_response_field"
       value="manual_challenge"
       />
</noscript>
"""


_CLIENT_USER_AGENT = \
    'reCAPTCHA Client by 2degrees (http://packages.python.org/recaptcha/)'


class RecaptchaClient(object):
    """Stateless reCAPTCHA client."""
    
    def __init__(
        self,
        private_key,
        public_key,
        recaptcha_options=None,
        verification_timeout=None,
        ):
        """
        
        :param private_key: The reCAPTCHA API private key
        :type private_key: :class:`str`
        :param public_key: The reCAPTCHA API public key
        :type public_key: :class:`str`
        :param recaptcha_options: Options to customize the challenge
        :type recaptcha_options: :class:`dict` that can be serialized to JSON
        :param verification_timeout: Maximum number of seconds to wait for
            reCAPTCHA to respond to a verification request
        :type verification_timeout: :class:`int`
        
        When ``verification_timeout`` is ``None``, the default socket timeout
        will be used. See :meth:`is_solution_correct`.
        
        """
        super(RecaptchaClient, self).__init__()
        
        self.private_key = private_key
        self.public_key = public_key
        
        self.recaptcha_options_json = json_encode(recaptcha_options or {})
        
        self.verification_timeout = verification_timeout
    
    def get_challenge_markup(
        self,
        was_previous_solution_incorrect=False,
        use_ssl=False,
        ):
        """
        Return the X/HTML code to present a challenge.
        
        :type was_previous_solution_incorrect: :class:`bool`
        :param use_ssl: Whether to generate the markup with HTTPS URLs instead
            of HTTP ones
        :type use_ssl: :class:`bool`
        :rtype: :class:`str`
        
        This method does not communicate with the remote reCAPTCHA API.
        
        """
        challenge_markup_variables = {
            'recaptcha_options_json': self.recaptcha_options_json,
            }
        
        challenge_urls = self._get_challenge_urls(
            was_previous_solution_incorrect,
            use_ssl,
            )
        challenge_markup_variables.update(challenge_urls)
        
        challenge_markup = _RECAPTCHA_CHALLENGE_MARKUP_TEMPLATE.format(
            **challenge_markup_variables
            )
        return challenge_markup
    
    def is_solution_correct(self, solution_text, challenge_id, remote_ip):
        """
        Report whether the ``solution_text`` for ``challenge_id`` is correct.
        
        :param solution_text: The user's solution to the CAPTCHA challenge
            identified by ``challenge_id``
        :type solution_text: :class:`basestring`
        :type challenge_id: :class:`str`
        :param remote_ip: The IP address of the user who provided the
            ``solution_text``
        :type remote_ip: :class:`str`
        :rtype: :class:`bool`
        :raises RecaptchaInvalidChallengeError: If ``challenge_id`` is not valid
        :raises RecaptchaInvalidPrivateKeyError:
        :raises RecaptchaUnreachableError: If it couldn't communicate with the
            reCAPTCHA API or the connection timed out
        
        ``solution_text`` must be a string encoded in
        :const:`RECAPTCHA_CHARACTER_ENCODING`.
        
        This method communicates with the remote reCAPTCHA API and uses the
        ``verification_timeout`` set in the constructor.
        
        """
        if not solution_text or not challenge_id:
            return False
        
        solution_text_decoded = \
            solution_text.decode(RECAPTCHA_CHARACTER_ENCODING)
        verification_result = self._get_recaptcha_response_for_solution(
            solution_text_decoded,
            challenge_id,
            remote_ip,
            )
        
        is_solution_correct = verification_result['is_solution_correct']
        
        if not is_solution_correct:
            error_code = verification_result['error_code']
            if error_code == 'invalid-request-cookie':
                raise RecaptchaInvalidChallengeError(challenge_id)
            elif error_code == 'invalid-site-private-key':
                raise RecaptchaInvalidPrivateKeyError(self.private_key)
        
        return is_solution_correct
    
    def _get_challenge_urls(
        self,
        was_previous_solution_incorrect,
        use_ssl,
        ):
        url_query_components = {'k': self.public_key}
        if was_previous_solution_incorrect:
            url_query_components['error'] = 'incorrect-captcha-sol'
        url_query_encoded = urlencode(url_query_components)
        
        javascript_challenge_url = _get_recaptcha_api_call_url(
            use_ssl,
            _RECAPTCHA_JAVASCRIPT_CHALLENGE_RELATIVE_URL_PATH,
            url_query_encoded,
            )
        
        noscript_challenge_url = _get_recaptcha_api_call_url(
            use_ssl,
            _RECAPTCHA_NOSCRIPT_CHALLENGE_RELATIVE_URL_PATH,
            url_query_encoded,
            )
        
        challenge_urls = {
            'javascript_challenge_url': javascript_challenge_url,
            'noscript_challenge_url': noscript_challenge_url,
            }
        return challenge_urls
    
    def _get_recaptcha_response_for_solution(
        self,
        solution_text_decoded,
        challenge_id,
        remote_ip,
        ):
        verification_url = _get_recaptcha_api_call_url(
            use_ssl=True,
            relative_url_path=_RECAPTCHA_VERIFICATION_RELATIVE_URL_PATH,
            )
        request_data = urlencode({
            'privatekey': self.private_key,
            'remoteip': remote_ip,
            'challenge': challenge_id,
            'response': solution_text_decoded,
            })
        request = Request(
            url=verification_url,
            data=request_data,
            headers={'User-agent': _CLIENT_USER_AGENT},
            )
        
        urlopen_kwargs = {}
        if self.verification_timeout is not None:
            urlopen_kwargs['timeout'] = self.verification_timeout
        try:
            response = urlopen(request, **urlopen_kwargs)
        except URLError, exc:
            raise RecaptchaUnreachableError(exc)
        else:
            response_lines = response.read().splitlines()
            response.close()
        
        is_solution_correct = response_lines[0] == 'true'
        verification_result = {'is_solution_correct': is_solution_correct}
        if not is_solution_correct:
            verification_result['error_code'] = response_lines[1]
        
        return verification_result


#{ Exceptions


class RecaptchaException(Exception):
    """Base class for all reCAPTCHA-related exceptions."""
    pass


class RecaptchaInvalidPrivateKeyError(RecaptchaException):
    pass


class RecaptchaInvalidChallengeError(RecaptchaException):
    pass


class RecaptchaUnreachableError(RecaptchaException):
    pass


#{ Utilities


def _get_recaptcha_api_call_url(use_ssl, relative_url_path, encoded_query=''):
    url_scheme = 'https' if use_ssl else 'http'
    
    recaptcha_api_url_components = urlsplit(_RECAPTCHA_API_URL)
    url_path = urljoin(
        recaptcha_api_url_components.path,
        relative_url_path,
        )
    
    url = urlunsplit((
        url_scheme,
        recaptcha_api_url_components.netloc,
        url_path,
        encoded_query,
        '',
        ))
    return url


#}
