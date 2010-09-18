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

"""Handler for retrieving uploaded photos for display."""

import model
import utils


class Photo(utils.Handler):
    def get(self):
        if not self.params.id:
            return self.error(404, 'No photo id was specified.')
        photo = model.Photo.get_by_id(int(self.params.id))
        if not photo:
            return self.error(404, 'There is no photo for the specified id.')
        self.response.headers['Content-Type'] = "image/png"
        self.response.out.write(photo.bin_data)

if __name__ == '__main__':
    utils.run(('/photo', Photo))
