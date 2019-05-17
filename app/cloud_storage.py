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


class CloudStorage(object):
    """A class to use Google Cloud Storage.
    
    It uses the application default credentials and the default Cloud Storage
    bucket for the App Engine app.
    
    If you use this class in the dev app server, you need to:
      1. Manually set up the application default credentials using:
           $ gcloud auth application-default login
      2. Point config "gcs_bucket_name" to a valid Cloud Storage bucket name,
         which allows read/write access from the credentials above.

    This class currently only supports a single object lifetime applied to all
    objects in the bucket, by set_objects_lifetime().
    If you want to store objects with different lifetimes, you may extend this
    class to either:
      - store objects in multiple buckets
      - set object holds:
        https://cloud.google.com/storage/docs/bucket-lock#object-holds
    """

    def __init__(self):
        credentials = GoogleCredentials.get_application_default()
        self.service = build('storage', 'v1', credentials=credentials)
        self.bucket_name = (
            config.get('gcs_bucket_name') or
            app_identity.get_default_gcs_bucket_name()).encode('utf-8')

    def insert_object(self, object_name, content_type, data):
        """Uploads an object to the bucket.
        
        Args:
            object_name (str): Name of the object.
            content_type (str): MIME type string of the object.
            data (str): The content of the object.
        """
        media = MediaIoBaseUpload(StringIO.StringIO(data), mimetype=content_type)
        self.service.objects().insert(
            bucket=self.bucket_name,
            name=object_name,
            body={
                # This let browsers to download the file instead of opening
                # it in a browser.
                'contentDisposition':
                    'attachment; filename=%s' % object_name,
            },
            media_body=media).execute()

    def compose_objects(
        self,
        source_object_names,
        destination_object_name,
        destination_content_type):
        """Concatenates the source objects to generate the destination object.
        
        Args:
            source_object_names (list of str): Names of the source objects.
            destination_object_name (str): Name of the destination object.
            destination_content_type (str): MIME type of the destination object.
        """
        self.service.objects().compose(
            destinationBucket=self.bucket_name,
            destinationObject=destination_object_name,
            body={
                'sourceObjects': [{'name': name} for name in source_object_names],
                'destination': {
                    'contentType': destination_content_type,
                    # This let browsers to download the file instead of opening
                    # it in a browser.
                    'contentDisposition':
                       'attachment; filename=%s' % destination_object_name,
                },
            }).execute()

    def sign_url(self, object_name, url_lifetime):
        """ Generates Cloud Storage signed URL to download Google Cloud Storage
        object without sign in.

        See: https://cloud.google.com/storage/docs/access-control/signed-urls
        
        This only works on a real App Engine app, not in a dev app server.
        
        Args:
            object_name (str): The name of the object which is signed.
            url_lifetime (datetime.timedelta): Lifetime of the signed URL. The
                server rejects any requests received after this time from now.
        """
        if utils.is_dev_app_server():
            # Not working on a dev app server because it doesn't support
            # app_identity.sign_blob(). An alternative implementation would
            # be needed to make it work on a dev app server.
            raise Exception(
                'sign_url only works on a real App Engine app, not on a dev '
                'app server.')

        method = 'GET'
        expiration_time = utils.get_utcnow() + url_lifetime
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
        (_, signature) = app_identity.sign_blob(signed_text.encode('utf-8'))

        query_params = {
            'GoogleAccessId': app_identity.get_service_account_name(),
            'Expires': str(expiration_sec),
            'Signature': base64.b64encode(signature),
        }
        return 'https://storage.googleapis.com%s?%s' % (path, urllib.urlencode(query_params))

    def set_objects_lifetime(self, lifetime_days):
        """Sets lifetime of all objects in the bucket in days.
        
        An object is deleted the specified days after it is created.

        lifetime_days (int): Lifetime of objects in a number of days.
        """
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
