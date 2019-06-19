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

import StaticPageWrapper from './../components/StaticPageWrapper.js';
import Zippy from './../components/Zippy.js';

const MESSAGES = defineMessages({
  infoForResponders: {
    id: 'RespondersPage.infoForResponders',
    defaultMessage: 'Information for responders',
    description: ('A header for a page with information about the product for '
        + 'responders (e.g., government or NGO employees) to a disaster.'),
  },
});

/**
 * A page for information for responders.
 */
class RespondersPage extends Component {
  constructor(props) {
    super(props);
    this.state = {
      showOwnInfoSection: false,
      showViewOthersInfoSection: false,
      showProvideOthersInfoSection: false,
    };
  }

  render() {
    return (
      <StaticPageWrapper
          pageTitle={"Help document"}>
        <h2 className='mdc-typography--subtitle2'>
          <FormattedMessage {...MESSAGES.infoForResponders} />
        </h2>
        <p className='mdc-typography--body1'>
          Any time Google launches Google Person Finder in response to a crisis, government and nonprofit organizations can help people locate each other by spreading the word, usign the data, and adding information.
        </p>
        <b>Embed Google Person Finder in your site</b>
        <p>Spread the word about Google Person Finder to your community. You can point people to <a href="https://google.org/personfinder">this Google Person Finder page</a>, or you can embed a small version of Google Person Finder directly on  your website using the following HTML code:</p>
        <pre>
          &lt;iframe
    src="https://google.org/personfinder/repository/?ui=small"
    width=400 height=300 frameborder=0
    style="border: dashed 2px #77c">&lt;/iframe>
        </pre>
        <p>(Replace <i>repository</i> with the appropriate repository name.)</p>
        <p>The above gadget code is made available under the Apache 2.0 license, and any data you receive in connection with the gadget is shared under a Create Commons license.</p>
        <b>Download data from Google Person Finder</b>
        <p>You can download the data in Google Person Finder or synchronize it with your own database using the Google Person Finder API. The information is provided in People Finder Interchange Format (PFIF), which is based on XML. See the <a href="https://github.com/google/personfinder/wiki/DataAPI">Person Finder code site</a> for detailed instructions on requesting access and downloading data.</p>
        <b>Upload data into Google Person Finder</b>
        <p>Add information from your database to Google Person Finder to make it available to the public and get the crowd to add what they know to the records. You will need to format your data in People Finder Interchange Format (PFIF) in order to upload it into Google Person Finder. See the <a href="https://github.com/google/personfinder/wiki/DataAPI">Person Finder code site</a> for detailed instructions on requesting access and uploading data.</p>
      </StaticPageWrapper>
    );
  }
}

export default injectIntl(RespondersPage);
