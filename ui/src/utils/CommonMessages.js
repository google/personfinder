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

const COMMON_MESSAGES = defineMessages({
  no: {
    id: 'CommonMessages.no',
    defaultMessage: 'No',
    description: 'A negative answer to a yes/no question.',
  },
  yes: {
    id: 'CommonMessages.yes',
    defaultMessage: 'Yes',
    description: 'An affirmative answer to a yes/no question.',
  },
});

export default COMMON_MESSAGES;
