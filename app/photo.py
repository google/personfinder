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

"""Handler for retrieving uploaded photos for display."""

import os

import model
import utils

from django.utils.translation import ugettext_lazy as _
from google.appengine.api import images
from google.appengine.runtime.apiproxy_errors import RequestTooLargeError

MAX_IMAGE_DIMENSION = 300
MAX_THUMBNAIL_DIMENSION = 80

class PhotoError(Exception):
    message = _('There was a problem processing the image.  '
                'Please try a different image.')

class FormatUnrecognizedError(PhotoError):
    message = _('Photo uploaded is in an unrecognized format.  '
                'Please go back and try again.')

class SizeTooLargeError(PhotoError):
    message = _('The provided image is too large.  '
                'Please upload a smaller one.')


def create_photo(image, repo, url_builder):
    """Creates a new Photo entity for the provided image of type images.Image
    after resizing it and converting to PNG.  It may throw a PhotoError on
    failure, which comes with a localized error message appropriate for
    display."""
    if image == False:  # False means it wasn't valid (see validate_image)
        raise FormatUnrecognizedError()

    if max(image.width, image.height) <= MAX_IMAGE_DIMENSION:
        # No resize needed.  Keep the same size but add a transformation to
        # force re-encoding.
        image.resize(image.width, image.height)
    elif image.width > image.height:
        image.resize(MAX_IMAGE_DIMENSION,
                     image.height * MAX_IMAGE_DIMENSION / image.width)
    else:
        image.resize(image.width * MAX_IMAGE_DIMENSION / image.height,
                     MAX_IMAGE_DIMENSION)

    try:
        image_data = image.execute_transforms(output_encoding=images.PNG)
    except RequestTooLargeError:
        raise SizeTooLargeError()
    except Exception:
        # There are various images.Error exceptions that can be raised, as well
        # as e.g. IOError if the image is corrupt.
        raise PhotoError()

    photo = model.Photo.create(repo, image_data=image_data)
    photo_url = get_photo_url(photo, repo, url_builder)
    return (photo, photo_url)


def set_thumbnail(photo):
    """Sets thumbnail data for a photo.

    Args:
        photo: the Photo object to set the thumbnail for
    """
    image = images.Image(photo.image_data)
    if max(image.width, image.height) <= MAX_THUMBNAIL_DIMENSION:
        # Don't need a thumbnail, it's small enough already.
        return
    elif image.width > image.height:
        image.resize(MAX_THUMBNAIL_DIMENSION,
                     image.height * MAX_THUMBNAIL_DIMENSION / image.width)
    else:
        image.resize(image.width * MAX_THUMBNAIL_DIMENSION / image.height,
                     MAX_THUMBNAIL_DIMENSION)
    try:
        thumbnail_data = image.execute_transforms(output_encoding=images.PNG)
    except RequestTooLargeError:
        raise SizeTooLargeError()
    except Exception:
        # There are various images.Error exceptions that can be raised, as well
        # as e.g. IOError if the image is corrupt.
        raise PhotoError()

    photo.thumbnail_data = thumbnail_data
    photo.save()


def get_photo_url(photo, repo, url_builder):
    """Returns the URL where this app is serving a hosted Photo object."""
    id = photo.key().name().split(':')[1]
    return url_builder('/photo', repo=repo, params=[('id', id)])


class Handler(utils.BaseHandler):
    def get(self):
        try:
            id = int(self.params.id)
        except:
            return self.error(404, 'Photo id is unspecified or invalid.')
        photo = model.Photo.get(self.repo, id)
        if not photo:
            return self.error(404, 'There is no photo for the specified id.')
        self.response.headers['Content-Type'] = 'image/png'
        self.response.headers['X-Content-Type-Options'] = 'nosniff'
        if self.params.thumb and photo.thumbnail_data:
            self.response.out.write(photo.thumbnail_data)
        else:
            self.response.out.write(photo.image_data)
