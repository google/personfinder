olefile (formerly OleFileIO\_PL)
================================

|Build Status| |Coverage Status| |Documentation Status|

`olefile <https://www.decalage.info/olefile>`__ is a Python package to
parse, read and write `Microsoft OLE2
files <http://en.wikipedia.org/wiki/Compound_File_Binary_Format>`__
(also called Structured Storage, Compound File Binary Format or Compound
Document File Format), such as Microsoft Office 97-2003 documents,
vbaProject.bin in MS Office 2007+ files, Image Composer and FlashPix
files, Outlook messages, StickyNotes, several Microscopy file formats,
McAfee antivirus quarantine files, etc.

**Quick links:** `Home page <https://www.decalage.info/olefile>`__ -
`Download/Install <http://olefile.readthedocs.io/en/latest/Install.html>`__
- `Documentation <http://olefile.readthedocs.io/en/latest>`__ - `Report
Issues/Suggestions/Questions <https://github.com/decalage2/olefile/issues>`__
- `Contact the author <https://www.decalage.info/contact>`__ -
`Repository <https://github.com/decalage2/olefile>`__ - `Updates on
Twitter <https://twitter.com/decalage2>`__

News
----

Follow all updates and news on Twitter: https://twitter.com/decalage2

-  **2017-01-06 v0.44**: several bugfixes, removed support for Python
   2.5 (olefile2), added support for incomplete streams and incorrect
   directory entries (to read malformed documents), added getclsid,
   improved `documentation <http://olefile.readthedocs.io/en/latest>`__
   with API reference.
-  2017-01-04: moved the documentation to
   `ReadTheDocs <http://olefile.readthedocs.io/en/latest>`__
-  2016-05-20: moved olefile repository to
   `GitHub <https://github.com/decalage2/olefile>`__
-  2016-02-02 v0.43: fixed issues
   `#26 <https://github.com/decalage2/olefile/issues/26>`__ and
   `#27 <https://github.com/decalage2/olefile/issues/27>`__, better
   handling of malformed files, use python logging.
-  2015-01-25 v0.42: improved handling of special characters in
   stream/storage names on Python 2.x (using UTF-8 instead of Latin-1),
   fixed bug in listdir with empty storages.
-  2014-11-25 v0.41: OleFileIO.open and isOleFile now support OLE files
   stored in byte strings, fixed installer for python 3, added support
   for Jython (Niko Ehrenfeuchter)
-  2014-10-01 v0.40: renamed OleFileIO\_PL to olefile, added initial
   write support for streams >4K, updated doc and license, improved the
   setup script.
-  2014-07-27 v0.31: fixed support for large files with 4K sectors,
   thanks to Niko Ehrenfeuchter, Martijn Berger and Dave Jones. Added
   test scripts from Pillow (by hugovk). Fixed setup for Python 3
   (Martin Panter)
-  2014-02-04 v0.30: now compatible with Python 3.x, thanks to Martin
   Panter who did most of the hard work.
-  2013-07-24 v0.26: added methods to parse stream/storage timestamps,
   improved listdir to include storages, fixed parsing of direntry
   timestamps
-  2013-05-27 v0.25: improved metadata extraction, properties parsing
   and exception handling, fixed `issue
   #12 <https://github.com/decalage2/olefile/issues/12>`__
-  2013-05-07 v0.24: new features to extract metadata (get\_metadata
   method and OleMetadata class), improved getproperties to convert
   timestamps to Python datetime
-  2012-10-09: published
   `python-oletools <https://www.decalage.info/python/oletools>`__, a
   package of analysis tools based on OleFileIO\_PL
-  2012-09-11 v0.23: added support for file-like objects, fixed `issue
   #8 <https://github.com/decalage2/olefile/issues/8>`__
-  2012-02-17 v0.22: fixed issues #7 (bug in getproperties) and #2
   (added close method)
-  2011-10-20: code hosted on bitbucket to ease contributions and bug
   tracking
-  2010-01-24 v0.21: fixed support for big-endian CPUs, such as PowerPC
   Macs.
-  2009-12-11 v0.20: small bugfix in OleFileIO.open when filename is not
   plain str.
-  2009-12-10 v0.19: fixed support for 64 bits platforms (thanks to Ben
   G. and Martijn for reporting the bug)
-  see changelog in source code for more info.

Download/Install
----------------

If you have pip or setuptools installed (pip is included in Python
2.7.9+), you may simply run **pip install olefile** or **easy\_install
olefile** for the first installation.

To update olefile, run **pip install -U olefile**.

Otherwise, see http://olefile.readthedocs.io/en/latest/Install.html

Features
--------

-  Parse, read and write any OLE file such as Microsoft Office 97-2003
   legacy document formats (Word .doc, Excel .xls, PowerPoint .ppt,
   Visio .vsd, Project .mpp), Image Composer and FlashPix files, Outlook
   messages, StickyNotes, Zeiss AxioVision ZVI files, Olympus FluoView
   OIB files, etc
-  List all the streams and storages contained in an OLE file
-  Open streams as files
-  Parse and read property streams, containing metadata of the file
-  Portable, pure Python module, no dependency

olefile can be used as an independent package or with PIL/Pillow.

olefile is mostly meant for developers. If you are looking for tools to
analyze OLE files or to extract data (especially for security purposes
such as malware analysis and forensics), then please also check my
`python-oletools <https://www.decalage.info/python/oletools>`__, which
are built upon olefile and provide a higher-level interface.

Documentation
-------------

Please see the `online
documentation <http://olefile.readthedocs.io/en/latest>`__ for more
information.

Real-life examples
------------------

A real-life example: `using OleFileIO\_PL for malware analysis and
forensics <http://blog.gregback.net/2011/03/using-remnux-for-forensic-puzzle-6/>`__.

See also `this
paper <https://computer-forensics.sans.org/community/papers/gcfa/grow-forensic-tools-taxonomy-python-libraries-helpful-forensic-analysis_6879>`__
about python tools for forensics, which features olefile.

License
-------

olefile (formerly OleFileIO\_PL) is copyright (c) 2005-2017 Philippe
Lagadec (https://www.decalage.info)

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

-  Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
-  Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

--------------

olefile is based on source code from the OleFileIO module of the Python
Imaging Library (PIL) published by Fredrik Lundh under the following
license:

The Python Imaging Library (PIL) is

-  Copyright (c) 1997-2009 by Secret Labs AB
-  Copyright (c) 1995-2009 by Fredrik Lundh

By obtaining, using, and/or copying this software and/or its associated
documentation, you agree that you have read, understood, and will comply
with the following terms and conditions:

Permission to use, copy, modify, and distribute this software and its
associated documentation for any purpose and without fee is hereby
granted, provided that the above copyright notice appears in all copies,
and that both that copyright notice and this permission notice appear in
supporting documentation, and that the name of Secret Labs AB or the
author not be used in advertising or publicity pertaining to
distribution of the software without specific, written prior permission.

SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO
THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS. IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR BE LIABLE FOR
ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

.. |Build Status| image:: https://travis-ci.org/decalage2/olefile.svg?branch=master
   :target: https://travis-ci.org/decalage2/olefile
.. |Coverage Status| image:: https://coveralls.io/repos/github/decalage2/olefile/badge.svg?branch=master
   :target: https://coveralls.io/github/decalage2/olefile?branch=master
.. |Documentation Status| image:: http://readthedocs.org/projects/olefile/badge/?version=latest
   :target: http://olefile.readthedocs.io/en/latest/?badge=latest
