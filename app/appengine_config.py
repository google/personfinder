#!/usr/bin/python2.7

import os

from google.appengine.ext import vendor

vendor.add(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'vendors'))
