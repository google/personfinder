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

"""Importing this module fixes an encoding bug in Django 0.96 templates."""

import django.template


def force_unicode(s, encoding='utf-8', errors='strict'):
    """Converts a string to Unicode.  Backported from django/utils/encoding.py
    in Django 1.1, without the fancy exception handling."""
    if not isinstance(s, basestring):
        if hasattr(s, '__unicode__'):
            return unicode(s)
        return unicode(str(s), encoding, errors)
    elif not isinstance(s, unicode):
        return s.decode(encoding, errors)
    return s

def NodeList_render(self, context):
    """A replacement for NodeList.render, backported from Django 1.1."""
    bits = []
    for node in self:
        if isinstance(node, django.template.Node):
            bits.append(self.render_node(node, context))
        else:
            bits.append(node)
    return ''.join(map(force_unicode, bits))

# Monkey-patch the fix into the NodeList class.
django.template.NodeList.render = NodeList_render

# Remove the broken __str__ method on the TemplateSyntaxError class.
del django.template.TemplateSyntaxError.__str__
