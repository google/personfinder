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
import {Link} from 'react-router-dom';

const messages = defineMessages({
  // TODO(nworden): figure out how to make this configurable for users other
  // than Google
  productName: {
    id: 'RepoHeader.productName',
    defaultMessage: 'Google Person Finder',
    description: ('Name of the product. Person Finder is a tool that helps '
        + 'people reconnect with friends/family after a disaster.'),
  },
});

class RepoHeader extends Component {
  render() {
    return (
      <div id='repoheader'>
        <div id='repoheader-backbutton'>
          <Link to={this.props.backButtonTarget}>
            <div><img src='/static/icons/maticon_arrow_back.svg' /></div>
          </Link>
        </div>
        <div id='repoheader-info'>
          <p className='mdc-typography--subtitle1'>
            <FormattedMessage {...messages.productName} />
          </p>
          <p className='mdc-typography--subtitle2'>
            {this.props.repo.title}
          </p>
        </div>
      </div>
    );
  }
}

export default injectIntl(RepoHeader);
