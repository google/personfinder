Unidecode, lossy ASCII transliterations of Unicode text
=======================================================

It often happens that you have text data in Unicode, but you need to
represent it in ASCII. For example when integrating with legacy code that
doesn't support Unicode, or for ease of entry of non-Roman names on a US
keyboard, or when constructing ASCII machine identifiers from
human-readable Unicode strings that should still be somewhat intelligible
(a popular example of this is when making an URL slug from an article
title). 

In most of these examples you could represent Unicode characters as
`???` or `\\15BA\\15A0\\1610`, to mention two extreme cases. But that's
nearly useless to someone who actually wants to read what the text says.

What Unidecode provides is a middle road: function `unidecode()` takes
Unicode data and tries to represent it in ASCII characters (i.e., the
universally displayable characters between 0x00 and 0x7F), where the
compromises taken when mapping between two character sets are chosen to be
near what a human with a US keyboard would choose.

The quality of resulting ASCII representation varies. For languages of
western origin it should be between perfect and good. On the other hand
transliteration (i.e., conveying, in Roman letters, the pronunciation
expressed by the text in some other writing system) of languages like
Chinese, Japanese or Korean is a very complex issue and this library does
not even attempt to address it. It draws the line at context-free
character-by-character mapping. So a good rule of thumb is that the further
the script you are transliterating is from Latin alphabet, the worse the
transliteration will be.

Note that this module generally produces better results than simply
stripping accents from characters (which can be done in Python with
built-in functions). It is based on hand-tuned character mappings that for
example also contain ASCII approximations for symbols and non-Latin
alphabets.

This is a Python port of `Text::Unidecode` Perl module by
Sean M. Burke <sburke@cpan.org>.


Module content
--------------

The module exports a function that takes an Unicode object (Python 2.x) or
string (Python 3.x) and returns a string (that can be encoded to ASCII bytes in
Python 3.x)::

    >>> from unidecode import unidecode
    >>> unidecode(u'ko\u017eu\u0161\u010dek')
    'kozuscek'
    >>> unidecode(u'30 \U0001d5c4\U0001d5c6/\U0001d5c1')
    '30 km/h'
    >>> unidecode(u"\u5317\u4EB0")
    'Bei Jing '

A utility is also included that allows you to transliterate text from the
command line in several ways. Reading from standard input::

    $ echo hello | unidecode
    hello

from a command line argument::

    $ unidecode -c hello
    hello

or from a file::

    $ unidecode hello.txt
    hello

The default encoding used by the utility depends on your system locale. You can specify another encoding with the `-e` argument. See `unidecode --help` for a full list of available options.

Requirements
------------

Nothing except Python itself.

You need a Python build with "wide" Unicode characters (also called "UCS-4
build") in order for unidecode to work correctly with characters outside of
Basic Multilingual Plane (BMP). Common characters outside BMP are bold, italic,
script, etc. variants of the Latin alphabet intended for mathematical notation.
Surrogate pair encoding of "narrow" builds is not supported in unidecode.

If your Python build supports "wide" Unicode the following expression will
return True::

    >>> import sys
    >>> sys.maxunicode > 0xffff
    True

See PEP 261 for details regarding support for "wide" Unicode characters in
Python.


Installation
------------

To install the latest version of Unidecode from the Python package index, use
these commands::

    $ pip install unidecode

To install Unidecode from the source distribution and run unit tests, use::

    $ python setup.py install
    $ python setup.py test


Performance notes
-----------------

By default, `unidecode` optimizes for the use case where most of the strings
passed to it are already ASCII-only and no transliteration is necessary (this
default might change in future versions).

For performance critical applications, two additional functions are exposed:

`unidecode_expect_ascii` is optimized for ASCII-only inputs (approximately 5
times faster than `unidecode_expect_nonascii` on 10 character strings, more on
longer strings), but slightly slower for non-ASCII inputs.

`unidecode_expect_nonascii` takes approximately the same amount of time on
ASCII and non-ASCII inputs, but is slightly faster for non-ASCII inputs than
`unidecode_expect_ascii`.

Apart from differences in run time, both functions produce identical results.
For most users of Unidecode, the difference in performance should be
negligible.


Source
------

You can get the latest development version of Unidecode with::

    $ git clone https://www.tablix.org/~avian/git/unidecode.git


Support
-------

Questions, bug reports, useful code bits, and suggestions for Unidecode
should be sent to tomaz.solc@tablix.org


Copyright
---------

Original character transliteration tables:

Copyright 2001, Sean M. Burke <sburke@cpan.org>, all rights reserved.

Python code and later additions:

Copyright 2016, Tomaz Solc <tomaz.solc@tablix.org>

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation; either version 2 of the License, or (at your option)
any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc., 51
Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.  The programs and
documentation in this dist are distributed in the hope that they will be
useful, but without any warranty; without even the implied warranty of
merchantability or fitness for a particular purpose.

..
    vim: set filetype=rst:


