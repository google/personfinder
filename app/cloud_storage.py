#!/usr/bin/python2.7
# Copyright 2018 Google Inc.
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

import base64
import datetime
import StringIO
import time
import urllib

from apiclient.http import MediaIoBaseUpload
from google.appengine.api import app_identity
from googleapiclient.discovery import build
from oauth2client.client import GoogleCredentials

import config
import utils


SIGNED_URL_LIFETIME = datetime.timedelta(minutes=10)


class CloudStorage(object):

    def __init__(self):
        # Note that you need to manually set up the application default credentials using:
        #   $ gcloud auth application-default login
        # on the dev app server.
        credentials = GoogleCredentials.get_application_default()
        self.service = build('storage', 'v1', credentials=credentials)
        self.bucket_name = (
            config.get('gcs_bucket_name') or app_identity.get_default_gcs_bucket_name()).encode('utf-8')

    def insert_object(self, object_name, content_type, data):
        media = MediaIoBaseUpload(StringIO.StringIO(data), mimetype=content_type)
        self.service.objects().insert(
            bucket=self.bucket_name,
            name=object_name,
            media_body=media).execute()

    def compose_objects(self, source_names, destination_name, destination_content_type):
        # Compose preferred over resumable because of 256KB chunk restriction
        self.service.objects().compose(
            destinationBucket=self.bucket_name,
            destinationObject=destination_name,
            body={
                'sourceObjects': [{'name': name} for name in source_names],
                'destination': {
                    'contentType': destination_content_type,
                    #'contentDisposition': 'attachment; filename=%s' % destination_name,
                },
            }).execute()

    def sign_url(self, object_name):
        """ Generates Google Cloud Storage signed URL to download Google Cloud Storage object without sign in.

        See: https://cloud.google.com/storage/docs/access-control/signed-urls
        """
        method = 'GET'
        expiration_time = utils.get_utcnow() + SIGNED_URL_LIFETIME
        expiration_sec = int(time.mktime(expiration_time.timetuple()))
        path = '/%s/%s' % (self.bucket_name, object_name)

        # These are unused in our use case.
        content_md5 = ''
        content_type = ''

        signed_text = '\n'.join([
            method,
            content_md5,
            content_type,
            str(expiration_sec),
            path,
        ])
        (_, signature) = app_identity.sign_blob(signed_text)

        query_params = {
            'GoogleAccessId': app_identity.get_service_account_name(),
            'Expires': str(expiration_sec),
            'Signature': base64.b64encode(signature),
        }
        return 'https://storage.googleapis.com%s?%s' % (path, urllib.urlencode(query_params))

    def set_objects_lifetime(self, lifetime_days):
        self.service.buckets().patch(bucket=self.bucket_name, body={
            'lifecycle': {
                'rule': [
                    {
                        'action': {'type': 'Delete'},
                        'condition': {'age': lifetime_days},
                    },
                ],
            },
        }).execute()
