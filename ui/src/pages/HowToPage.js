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
  helpDocument: {
    id: 'HowToPage.helpDocument',
    defaultMessage: 'Help document',
    description: 'A header for a page with help documentation.',
  },
  intro: {
    id: 'HowToPage.intro',
    defaultMessage: ('Person Finder can be used by anyone from a PC or mobile '
        + 'phone. This document shows how to provide and search for safety '
        + 'information in emergency situations.'),
    description: 'An introduction to a user guide for Person Finder.',
  },
  pfUserGuide: {
    id: 'HowToPage.pfUserGuide',
    defaultMessage: 'Person Finder User\'s Guide',
    description: 'A header for a user guide page.',
  },
});

/**
 * A page for the user guide.
 */
class HowToPage extends Component {
  constructor(props) {
    super(props);
    this.state = {
      showOwnInfoSection: true,
      showViewOthersInfoSection: false,
      showProvideOthersInfoSection: false,
    };
  }

  render() {
    return (
      <StaticPageWrapper
          pageTitle={this.props.intl.formatMessage(MESSAGES.helpDocument)}>
        <h2 className='mdc-typography--subtitle2'>
          <FormattedMessage {...MESSAGES.pfUserGuide} />
        </h2>
        <p className='mdc-typography--body1'>
          <FormattedMessage {...MESSAGES.intro} />
        </p>
        <ul className='staticpage-sectionzippylist'>
          <li>
            <Zippy
                header={'Provide your own safety information'}
                zipHandler={
                  (display) => this.setState({showOwnInfoSection: display})}
                display={this.state.showOwnInfoSection}>
              <ol className='mdc-typography--body1'>
                <li>
                  <b>Getting started</b>
                  <p>Go to the Google Person Finder homepage by entering the URL (<a href="http://g.co/pf">http://g.co/pf</a>) in the browser and choose the disaster name relevant to you. Here is an environment for demonstration so you can try the operation at any time.</p>
                </li>
                <li>
                  <b>Enter your name</b>
                  <p>Put your name in [Given name] [Family name] and click [Provide information about this person].</p>
                </li>
                <li>
                  <b>Finish moving this page to React</b>
                  <p>Nick's not done with this yet.</p>
                </li>
              </ol>
            </Zippy>
          </li>
        </ul>
      </StaticPageWrapper>
    );
  }
}

export default injectIntl(HowToPage);
