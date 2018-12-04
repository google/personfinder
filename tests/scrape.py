# Copyright 2005-2012 Ka-Ping Yee
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

"""Python module for web browsing and scraping.

Features:
  - navigate to absolute and relative URLs
  - follow links in page or region
  - find elements with lxml
  - set form fields
  - submit forms
  - support HTTPS
  - handle entities > 255 and Unicode documents
  - accept and store cookies during redirection
  - store and send cookies according to domain and path
  - submit forms with file upload
"""
from __future__ import print_function

__author__ = 'Ka-Ping Yee <ping@zesty.ca>'
__date__ = '$Date: 2012/09/22 00:00:00 $'.split()[1].replace('/', '-')
__version__ = '$Revision: 2.00 $'

from urlparse import urlsplit, urljoin
import re
import sys

import lxml.etree

RE_TYPE = type(re.compile(''))

class ScrapeError(Exception):
    pass

def request(scheme, method, host, path, headers, data='', verbose=0):
    """Make an HTTP or HTTPS request; return the entire reply as a string."""
    request = method + ' ' + path + ' HTTP/1.0\r\n'
    for name, value in headers.items():
        capname = '-'.join([part.capitalize() for part in name.split('-')])
        request += capname + ': ' + str(value) + '\r\n'
    request += '\r\n' + data
    host, port = host.split('@')[-1], [80, 443][scheme == 'https']
    if ':' in host:
        host, port = host.split(':', 1)

    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if verbose >= 3:
        print('connect:', host, port, file=sys.stderr)
    sock.connect((host, int(port)))
    file = scheme == 'https' and socket.ssl(sock) or sock.makefile()
    if verbose >= 3:
        print(('\r\n' + request.rstrip()).replace(
            '\r\n', '\nrequest: ').lstrip(), file=sys.stderr)
    file.write(request)
    if hasattr(file, 'flush'):
        file.flush()
    chunks = []
    try:
        while not (chunks and len(chunks[-1]) == 0):
            chunks.append(file.read())
    except socket.error:
        pass
    return ''.join(chunks)

def shellquote(text):
    """Quote a string literal for /bin/sh."""
    return "'" + text.replace("'", "'\\''") + "'"

def curl(url, headers={}, data=None, verbose=0):
    """Use curl to make a request; return the entire reply as a string."""
    import os, tempfile
    fd, tempname = tempfile.mkstemp(prefix='scrape')
    command = 'curl --include --insecure --silent --max-redirs 0'
    if data:
        if not isinstance(data, str): # Unicode not allowed here
            data = urlencode(data)
        command += ' --data ' + shellquote(data)
    for name, value in headers.iteritems():
        command += ' --header ' + shellquote('%s: %s' % (name, value))
    command += ' ' + shellquote(url)
    if verbose >= 3:
        print('execute:', command, file=sys.stderr)
    os.system(command + ' > ' + tempname)
    reply = open(tempname).read()
    os.remove(tempname)
    return reply

def getcookies(cookiejar, host, path):
    """Get a dictionary of the cookies from 'cookiejar' that apply to the
    given request host and request path."""
    cookies = {}
    for cdomain in cookiejar:
        if ('.' + host).endswith(cdomain):
            for cpath in cookiejar[cdomain]:
                if path.startswith(cpath):
                    for key, value in cookiejar[cdomain][cpath].items():
                        cookies[key] = value
    return cookies

def setcookies(cookiejar, host, lines):
    """Store cookies in 'cookiejar' according to the given Set-Cookie
    header lines."""
    for line in lines:
        pairs = [(part.strip().split('=', 1) + [''])[:2]
                 for part in line.split(';')]
        (name, value), attrs = pairs[0], dict(pairs[1:])
        cookiejar.setdefault(attrs.get('domain', host), {}
                ).setdefault(attrs.get('path', '/'), {})[name] = value

RAW = object() # This sentinel value for 'charset' means "don't decode".

def fetch(url, data='', agent=None, referrer=None, charset=None, verbose=0,
          cookiejar={}, type=None, method=None, accept_language=None):
    """Make an HTTP or HTTPS request.

    If 'data' is given, do a POST; otherwise do a GET.

    If 'agent', 'referrer' and/or 'accept_language' are given, include them as
    User-Agent, Referer and Accept-Language headers in the request,
    respectively.

    'cookiejar' should have the form {domain: {path: {name: value, ...}}};
    cookies will be sent from it and received cookies will be stored in it.

    Return the 5-element tuple (url, status, message, headers, content)
    where 'url' is the final URL retrieved, 'status' is the integer status
    code, 'message' is the reply status message, 'headers' is a dictionary of
    HTTP headers, and 'content' is a string containing the received content.
    For multiple occurrences of the same header, 'headers' will contain a
    single key-value pair where the values are joined together with newlines.
    If the Content-Type header specifies a 'charset' parameter, 'content'
    will be a Unicode string, decoded using the given charset.

    Giving the 'charset' argument overrides any received 'charset' parameter; a
    charset of RAW ensures that the content is left undecoded in an 8-bit
    string.
    """
    scheme, host, path, query, fragment = urlsplit(url)
    host = host.split('@')[-1]

    # Prepare the POST data.
    if not method:
        method = data and 'POST' or 'GET'

    if not data:
        data_str = ''
    elif isinstance(data, str):
        data_str = data
    elif isinstance(data, unicode):
        data_str = data.encode('utf-8')
    elif isinstance(data, dict):
        # urlencode() supports both of a dict of str and a dict of unicode.
        data_str = urlencode(data)
    else:
        raise Exception('Unexpected type for data: %r' % data)

    # Get the cookies to send with this request.
    cookieheader = '; '.join([
        '%s=%s' % pair for pair in getcookies(cookiejar, host, path).items()])

    # Make the HTTP headers to send.
    headers = {'host': host, 'accept': '*/*'}
    if data_str:
        headers['content-type'] = 'application/x-www-form-urlencoded'
        headers['content-length'] = len(data_str)
    if agent:
        headers['user-agent'] = agent
    if referrer:
        headers['referer'] = referrer
    if cookieheader:
        headers['cookie'] = cookieheader
    if type:
        headers['content-type'] = type
    if accept_language:
        headers['accept-language'] = accept_language

    # Make the HTTP or HTTPS request using Python or cURL.
    if verbose:
        print('>', method, url, file=sys.stderr)
    import socket
    if scheme == 'http' or scheme == 'https' and hasattr(socket, 'ssl'):
        if query:
            path += '?' + query
        reply = request(scheme, method, host, path, headers, data_str, verbose)
    elif scheme == 'https':
        reply = curl(url, headers, data_str, verbose)
    else:
        raise ValueError, scheme + ' not supported'

    # Take apart the HTTP reply.
    headers, head, content = {}, reply, ''
    if '\r\n\r\n' in reply:
        head, content = (reply.split('\r\n\r\n', 1) + [''])[:2]
    else:  # Non-conformant reply.  Bummer!
        match = re.search('\r?\n[ \t]*\r?\n', reply)
        if match:
            head, content = head[:match.start()], head[match.end():]
    head = head.replace('\r\n', '\n').replace('\r', '\n')
    response, head = head.split('\n', 1)
    if verbose >= 3:
        print('reply:', response.rstrip(), file=sys.stderr)
    status = int(response.split()[1])
    message = ' '.join(response.split()[2:])
    for line in head.split('\n'):
        if verbose >= 3:
            print('reply:', line.rstrip(), file=sys.stderr)
        name, value = line.split(': ', 1)
        name = name.lower()
        if name in headers:
            headers[name] += '\n' + value
        else:
            headers[name] = value
    if verbose >= 2:
        print('content: %d byte%s\n' % (
            len(content), content != 1 and 's' or ''), file=sys.stderr)
    if verbose >= 3:
        for line in content.rstrip('\n').split('\n'):
            print('content: ' + repr(line + '\n'), file=sys.stderr)

    # Store any received cookies.
    if 'set-cookie' in headers:
        setcookies(cookiejar, host, headers['set-cookie'].split('\n'))

    return url, status, message, headers, content

def multipart_encode(data, charset):
    """Encode 'data' for a multipart post. If any of the values is of type file,
    the content of the file is read and added to the output. If any of the
    values is of type unicode, it is encoded using 'charset'. Returns a pair
    of the encoded string and content type string, which includes the multipart
    boundary used."""
    import mimetools, mimetypes
    boundary = mimetools.choose_boundary()
    encoded = []
    for key, value in data.iteritems():
        encoded.append('--%s' % boundary)
        if isinstance(value, file):
            fd = value
            filename = fd.name.split('/')[-1]
            content_type = (mimetypes.guess_type(filename)[0] or
                'application/octet-stream')
            encoded.append('Content-Disposition: form-data; ' +
                           'name="%s"; filename="%s"' % (key, filename))
            encoded.append('Content-Type: %s' % content_type)
            fd.seek(0)
            value = fd.read()
        else:
            encoded.append('Content-Disposition: form-data; name="%s"' % key)
            if isinstance(value, unicode):
                value = value.encode(charset)
        encoded.append('')  # empty line
        encoded.append(value)
    encoded.append('--' + boundary + '--')
    encoded.append('')  # empty line
    encoded.append('')  # empty line
    encoded = '\r\n'.join(encoded)
    content_type = 'multipart/form-data; boundary=%s' % boundary
    return encoded, content_type

class Session:
    """A Web-browsing session.  Exposed attributes:

        agent   - the User-Agent string (clients can set this attribute)
        url     - the last successfully fetched URL
        status  - the status code of the last request
        message - the status message of the last request
        headers - the headers of the last request as a dictionary
        content - the content of the last fetched document
        doc     - the Document instance currently opened.
    """

    def __init__(self, agent=None, verbose=0):
        """Specify 'agent' to set the User-Agent.  Set 'verbose' to 1, 2, or
        3 to display status messages on stderr during document retrieval."""
        self.agent = agent
        self.url = self.status = self.message = self.content = self.doc = None
        self.verbose = verbose
        self.headers = {}
        self.cookiejar = {}
        self.history = []

    def go(self, url_or_doc, data='', redirects=10, referrer=True,
           charset=None, type=None, accept_language=None):
        """Navigate to a given URL or a document.

        If the URL is relative, it is resolved with respect to the current URL.

        If 'data' is provided, do a POST; otherwise do a GET.

        Follow redirections up to 'redirects' times.

        If 'referrer' is given, send it as the referrer; if 'referrer' is
        True (default), send the current URL as the referrer; if 'referrer'
        is a false value, send no referrer.

        If 'charset' is given, it overrides any received 'charset' parameter;
        setting 'charset' to RAW leaves the content undecoded in an 8-bit
        string.

        If 'accept_language' is given, include it as Accept-Language headers in
        the request.

        If the document is successfully fetched, return a Document spanning the
        entire document. Any relevant previously stored cookies will be included
        in the request, and any received cookies will be stored for future use.

        If a scrape.Document instance is given, it just make it the current
        document (self.doc) in the session, without making any extra HTTP
        requests.
        """
        self.history.append(
            (self.url, self.status, self.message,
             self.headers, self.content, self.doc))

        if isinstance(url_or_doc, Document):
            self.doc = url_or_doc

        else:
            url = self.resolve(url_or_doc)
            if referrer is True:
                referrer = self.url

            while 1:
                (self.url, self.status, self.message, self.headers,
                 content_bytes) = fetch(
                    url=url,
                    data=data,
                    agent=self.agent,
                    referrer=referrer,
                    charset=charset,
                    verbose=self.verbose,
                    cookiejar=self.cookiejar,
                    type=type,
                    accept_language=accept_language)
                if redirects:
                    if self.status in [301, 302] and 'location' in self.headers:
                        url, data = urljoin(url, self.headers['location']), ''
                        redirects -= 1
                        continue
                break

            self.doc = Document(
                content_bytes,
                url=self.url,
                status=self.status,
                message=self.message,
                headers=self.headers,
                charset=charset)

        self.url = self.doc.url
        self.content = self.doc.content
        self.status = self.doc.status
        self.message = self.doc.message
        self.headers = self.doc.headers
        self.charset = self.doc.charset
        return self.doc

    def back(self):
        """Restore the state of this session before the previous request."""
        (self.url, self.status, self.message,
         self.headers, self.content, self.doc) = self.history.pop()
        return self.url

    def follow(self, anchor, context=None):
        """If 'anchor' is an element, follow the link in its 'href' attribute;
        if 'anchor' is a string or compiled RE, find the first link with that
        anchor text, and follow it.  If 'context' is specified, a matching link
        is searched only inside the 'context' element, instead of the whole
        document.

        e.g.:
          self.s.follow('Click here')
          self.s.follow(self.s.doc.cssselect_one('a.link'))
        """
        if isinstance(anchor, basestring):
            link = None
            for l in (context or self.doc).cssselect('a'):
                if get_all_text(l) == anchor:
                    link = l
                    break
        elif isinstance(anchor, RE_TYPE):
            link = None
            for l in (context or self.doc).cssselect('a'):
                if re.search(anchor, get_all_text(l)):
                    link = l
                    break
        elif isinstance(anchor, lxml.etree._Element):
            link = anchor
        else:
            raise ScrapeError('Unexpected type for anchor: %r' % anchor)

        if link is None:
            raise ScrapeError('link %r not found' % anchor)
        href = link.get('href')
        if not href:
            raise ScrapeError('link %r has no href' % link)

        return self.go(href)

    def follow_button(self, button):
        """Follow the forward URL specified in the button's onclick handler."""
        if not button:
            raise ScrapeError('button %r not found' % button)
        location_match = re.search(r'location\.href=[\'"]([^\'"]+)',
                                   button.get('onclick', ''))
        if not location_match:
            raise ScrapeError('button %r has no forward URL' % button)
        return self.go(location_match.group(1))

    def submit(self, elem, paramdict=None, url=None, redirects=10, **params):
        """Submit a form, optionally by clicking a given button.  The 'elem'
        argument should be of type lxml.etree._Element and can be the form
        itself or a button in the form to click.  Obtain the parameters to
        submit by (a) starting with the 'paramdict' dictionary if specified, or
        the default parameter values as returned by get_form_params; then (b)
        adding or replacing parameters in this dictionary according to the
        keyword arguments.  The 'url' argument overrides the form's action
        attribute and submits the form elsewhere.  After submission, follow
        redirections up to 'redirects' times.

        e.g.:
          self.s.submit(self.s.doc.cssselect_one('form'))
          self.s.submit(self.s.doc.cssselect_one('input[type="submit"]'))
        """

        try:
            if elem.tag == 'form':
                form = elem
            else:
                form = elem.iterancestors('form').next()
        except IndexError:
            raise ScrapeError('%r is not contained in a form' % elem)
        form_params = get_form_params(form)

        p = paramdict.copy() if paramdict is not None else form_params
        # Include the (name, value) attributes of a submit button as part of the
        # parameters e.g. <input type="submit" name="action" value="add">
        if elem.get('name'):
            p[elem.get('name')] = elem.get('value', '')
        p.update(params)

        method = form.get('method', '').lower() or 'get'
        url = url or form.get('action', self.url)
        multipart_post = any(map(lambda v: isinstance(v, file), p.itervalues()))
        if multipart_post:
            param_str, content_type = multipart_encode(p, self.doc.charset)
        else:
            param_str, content_type = urlencode(p, self.doc.charset), None
        if method == 'get':
            if multipart_post:
                raise ScrapeError('can not upload a file with a GET request')
            return self.go(url + '?' + param_str, '', redirects)
        elif method == 'post':
            return self.go(url, param_str, redirects, type=content_type)
        else:
            raise ScrapeError('unknown form method %r' % method)

    def resolve(self, url):
        """Resolve a URL with respect to the current location."""
        if self.url and not (
            url.startswith('http://') or url.startswith('https://')):
            url = urljoin(self.url, url)
        return url

    def setcookie(self, cookieline):
        """Put a cookie in this session's cookie jar.  'cookieline' should
        have the format "<name>=<value>; domain=<domain>; path=<path>"."""
        scheme, host, path, query, fragment = urlsplit(self.url)
        host = host.split('@')[-1]
        setcookies(self.cookiejar, host, [cookieline])


urlquoted = dict((chr(i), '%%%02X' % i) for i in range(256))
urlquoted.update(dict((c, c) for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' +
                                      'abcdefghijklmnopqrstuvwxyz' +
                                      '0123456789._-'))

def urlquote(text, charset='utf-8'):
    if type(text) is unicode:
        text = text.encode(charset)
    return ''.join(map(urlquoted.get, text))

def urlencode(params, charset='utf-8'):
    pairs = ['%s=%s' % (
                 urlquote(key, charset),
                 urlquote(value, charset).replace('%20', '+'))
             for key, value in params.items()]
    return '&'.join(pairs)

class Document(object):
    """A document returned as an HTTP response.
    """

    def __init__(self, content_bytes, url, status, message, headers, charset):
        """charset is used to decode content_bytes. If charset is None, it uses
        the charset in headers['content-type'].
        """
        self.content_bytes = content_bytes
        self.url = url
        self.status = status
        self.message = message
        self.headers = headers
        self.charset = charset

        if 'content-type' in headers:
            fields = headers['content-type'].split(';')
            content_type = fields[0]
            for field in fields[1:]:
                if not self.charset and field.strip().startswith('charset='):
                    self.charset = field.strip()[8:]
                    break
        else:
            content_type = None

        if not content_bytes or self.charset == RAW:
            self.__etree_doc = None
        elif content_type == 'text/html':
            self.__etree_doc = lxml.etree.HTML(
                content_bytes,
                parser=lxml.etree.HTMLParser(encoding=self.charset))
        elif content_type in ['text/xml', 'application/xml']:
            self.__etree_doc = lxml.etree.XML(
                content_bytes,
                parser=lxml.etree.XMLParser(encoding=self.charset))
        else:
            self.__etree_doc = None

        if self.charset == RAW:
            self.content = content_bytes
        elif self.charset:
            self.content = content_bytes.decode(self.charset)
        else:
            self.content = None

        if self.__etree_doc is not None:
            self.text = get_all_text(self.__etree_doc)

    def cssselect(self, expr, **kwargs):
        """Evaluate a CSS selector expression against the document, and returns
        a list of lxml.etree._Element instances.

        e.g.,
          self.s.doc.cssselect('.my-class-name')

        See http://lxml.de/api/lxml.etree._Element-class.html#cssselect for
        details.

        This method is available only if:
          - the content-type is either text/html or text/xml
          - charset is known (either from charset parameter of the constructor
            or from the header)
          - charset is not RAW
        """
        return self.__get_etree_doc().cssselect(expr, **kwargs)

    def cssselect_one(self, expr, **kwargs):
        """Evaluate a CSS selector expression against the document, and returns
        a single lxml.etree._Element instance.

        Throws AssertionError if zero or multiple elements match the expression.

        e.g.,
          self.s.doc.cssselect_one('.my-class-name')

        See http://lxml.de/api/lxml.etree._Element-class.html#cssselect for
        details.

        This method is available only if:
          - the content-type is either text/html or text/xml
          - charset is known (either from charset parameter of the constructor
            or from the header)
          - charset is not RAW
        """
        elems = self.cssselect(expr, **kwargs)
        assert elems, (
            'cssselect_one(%r) was called, but there are no matching elements.'
                % expr)
        assert len(elems) == 1, (
            'cssselect_one(%r) was called, but there are multiple matching '
            'elements: %r' % (expr, elems))
        return elems[0]

    def xpath(self, path, **kwargs):
        """Evaluate an XPath expression against the document, and returns a
        list of lxml.etree.ElementBase instances.

        It is generally recommended to use cssselect() instead if it can be
        expressed with CSS selector.

        See http://lxml.de/api/lxml.etree._Element-class.html#xpath for
        details.

        This method is available only if:
          - the content-type is either text/html or text/xml
          - charset is known (either from charset parameter of the constructor
            or from the header)
          - charset is not RAW
        """
        return self.__get_etree_doc().xpath(path, **kwargs)

    def xpath_one(self, path, **kwargs):
        """Evaluate an XPath expression against the document, and returns a
        single lxml.etree.ElementBase instance.

        Throws AssertionError if zero or multiple elements match the expression.

        It is generally recommended to use cssselect() instead if it can be
        expressed with CSS selector.

        See http://lxml.de/api/lxml.etree._Element-class.html#xpath for
        details.

        This method is available only if:
          - the content-type is either text/html or text/xml
          - charset is known (either from charset parameter of the constructor
            or from the header)
          - charset is not RAW
        """
        elems = self.__get_etree_doc().xpath(path, **kwargs)
        assert elems, (
            'xpath_one(%r) was called, but there are no matching elements.'
                % path)
        assert len(elems) == 1, (
            'xpath_one(%r) was called, but there are multiple matching '
            'elements: %r' % (path, elems))
        return elems[0]

    def __get_etree_doc(self):
        assert self.__etree_doc is not None, (
            'The content type is neither text/html nor text/xml, '
            'charset is RAW, or the document is empty.')
        return self.__etree_doc


def read(path):
    """Read and return the entire contents of the file at the given path."""
    return open(path).read()

def write(path, text):
    """Write the given text to a file at the given path."""
    file = open(path, 'w')
    file.write(text)
    file.close()

def load(path):
    """Return the deserialized contents of the file at the given path."""
    import marshal
    return marshal.load(open(path))

def dump(path, data):
    """Serialize the given data and write it to a file at the given path."""
    import marshal
    file = open(path, 'w')
    marshal.dump(data, file)
    file.close()

def get_all_text(elem):
    """Returns all texts in the subtree of the lxml.etree._Element, which is
    returned by Document.cssselect() etc.
    """
    text = ''.join(elem.itertext())
    return re.sub(r'\s+', ' ', text).strip()

def get_all_attrs(elem):
    """Returns attribute and value pairs from all the elements in the subtree
    of lxml.etree._Element, including the given element.
    """
    attrs = []
    for e in elem.iter():
        attrs += e.attrib.items()
    return attrs

def get_form_params(form):
    """Get a dictionary of default values for all the form parameters.
    If there is a <input type=file> tag, it tries to open a file object."""
    params = {}
    for input in form.cssselect('input'):
        if input.get('name') and input.get('disabled') is None:
            type = input.get('type', 'text').lower()
            if type in ['checkbox', 'radio']:
                add_value = input.get('checked') is not None
            elif type in ['file', 'submit', 'image', 'reset', 'button']:
                add_value = False
            else:
                # Ordinary input fields such as 'text' or 'hidden'. Note that
                # there are many types in this category in HTML5 like 'number'.
                add_value = True
            if add_value:
                params[input.get('name')] = input.get('value', '')
    for select in form.cssselect('select'):
        if select.get('disabled') is None:
            selections = [option.get('value', '')
                          for option in select.cssselect('option')
                          if option.get('selected') is not None]
            if select.get('multiple') is not None:
                params[select.get('name')] = selections
            elif selections:
                params[select.get('name')] = selections[0]
    for textarea in form.cssselect('textarea'):
        if textarea.get('disabled') is None:
            params[textarea.get('name')] = textarea.text or ''
    return params

s = Session()
