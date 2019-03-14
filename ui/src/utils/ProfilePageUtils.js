/*
 * Copyright 2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import {defineMessages} from 'react-intl';

const MESSAGES = defineMessages({
  facebook: {
    id: 'ProfilePageUtils.facebook',
    defaultMessage: 'Facebook',
    description: 'The social media site.',
  },
  twitter: {
    id: 'ProfilePageUtils.twitter',
    defaultMessage: 'Twitter',
    description: 'The social media site.',
  },
  linkedin: {
    id: 'ProfilePageUtils.linkedin',
    defaultMessage: 'LinkedIn',
    description: 'The networking site.',
  },
  otherWebsite: {
    id: 'ProfilePageUtils.otherWebsite',
    defaultMessage: 'Other website',
    description: ('A label for a button for users to add a link to a site '
        + 'other than a site on a pre-defined list.'),
  },
});

/**
 * A utility for people's profile pages.
 */
const ProfilePageUtils = Object.freeze({
  /**
   * A mapping from a profile page site ID to a MessageDescriptor of the name
   * of the site.
   */
  SITES: Object.freeze({
    'facebook': MESSAGES.facebook,
    'twitter': MESSAGES.twitter,
    'linkedin': MESSAGES.linkedin,
    'other': MESSAGES.otherWebsite,
  })
});

export default ProfilePageUtils;
