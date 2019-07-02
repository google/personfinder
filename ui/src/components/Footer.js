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
import {FormattedHTMLMessage, defineMessages, injectIntl} from 'react-intl';

const MESSAGES = defineMessages({
  disclaimerTextHTML: {
    id: 'Footer.disclaimerText',
    defaultMessage: ('PLEASE NOTE: All data entered is available to the public '
        + 'and usable by anyone. Google does not review or verify the accuracy '
        + 'of this data. Google may share the data with public and private '
        + 'organizations participating in disaster response efforts. Learn '
        + 'more about <a href="https://policies.google.com/privacy">Google\'s '
        + 'privacy policy</a>.'),
    description: 'A disclaimer shown at the footer of the page.',
  },
});

class Footer extends Component {
  render() {
    // Generally, the footer is separate from everything else. Sometimes though,
    // it's within a box; the box has some padding of its own, so the footer
    // should have less padding in those cases.
    const classNames = this.props.wrapped ?
        'footer footer-wrapped' : 'footer footer-unwrapped';
    return (
      <div className={classNames}>
        <p className='mdc-typography--body1'>
          <FormattedHTMLMessage {...MESSAGES.disclaimerTextHTML} />
        </p>
      </div>
    );
  }
}

export default injectIntl(Footer);
