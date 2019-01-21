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

import React, {Component} from 'react';
import {FormattedMessage, defineMessages, injectIntl} from 'react-intl';

const messages = defineMessages({
  disclaimerText: {
    id: 'Footer.disclaimerText',
    defaultMessage: ('PLEASE NOTE: All data entered is available to the public '
        + 'and usable by anyone. Google does not review or verify the accuracy '
        + 'of this data. Google may share the data with public and private '
        + 'organizations participating in disaster response efforts.'),
    description: 'A disclaimer shown at the footer of the page.',
  },
});

const Footer = () => (
  <div className="footer">
    <p className="mdc-typography--body1">
      <FormattedMessage {...messages.disclaimerText} />
    </p>
  </div>
);

export default injectIntl(Footer);
