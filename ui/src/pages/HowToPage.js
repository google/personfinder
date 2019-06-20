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
      showOwnInfoSection: false,
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
                header={
                    <h3 className='mdc-typography--headline3'>
                      Provide your own safety information
                    </h3>}
                zipHandler={
                    (display) => this.setState({showOwnInfoSection: display})}
                display={this.state.showOwnInfoSection}>
              {/* TODO(nworden): figure out how to i18n this, esp. if we need screenshots */}
              <ol className='mdc-typography--body1'>
                <li>
                  <b>Getting started</b>
                  <p>Go to the Google Person Finder homepage by entering the URL (<a href="http://g.co/pf">http://g.co/pf</a>) in the browser and choose the disaster name relevant to you. Then click the [Provide information about someone] button.</p>
                </li>
                <li>
                  <b>Enter your name</b>
                  <p>Put your name in the [Given name] [Family name] fields.</p>
                </li>
                <li>
                  <b>Input more detailed information (optional)</b>
                  <p>You can click the [More] button to open up fields for more detailed information, to help others identify you.</p>
                </li>
                <li>
                  <b>Specify your status</b>
                  <p>In the [Status of this person] field, select [I am this person]. Optionally, add your location.</p>
                </li>
                <li>
                  <b>Submit the record</b>
                  <p>Click [Submit record]. Your record will be created.</p>
                </li>
              </ol>
            </Zippy>
          </li>
          <li>
            <Zippy
                header={
                    <h3 className='mdc-typography--headline3'>
                      Confirm safety of family and friends
                    </h3>}
                zipHandler={
                    (display) => this.setState({
                        showViewOthersInfoSection: display})}
                display={this.state.showViewOthersInfoSection}>
              <ol className='mdc-typography--body1'>
                <li>
                  <b>Getting started</b>
                  <p>Go to the Google Person Finder homepage by entering the URL (<a href="http://g.co/pf">http://g.co/pf</a>) in the browser and choose the disaster name relevant to you.</p>
                </li>
                <li>
                  <b>Searching</b>
                  <p>Enter the name of the person you're looking for and then hit the [Enter] key.</p>
                </li>
                <li>
                  <b>Results</b>
                  <p>If you see a search result that might be the person you're looking for, click it to open a page with more details about that record.</p>
                </li>
                <li>
                  <b>Adding a record</b>
                  <p>If you can't find a record for the person you're looking for, you can add a record seeking information.</p>
                </li>
              </ol>
            </Zippy>
          </li>
          <li>
            <Zippy
                header={
                    <h3 className='mdc-typography--headline3'>
                      Provide other people's safety information
                    </h3>}
                zipHandler={
                    (display) => this.setState({
                      showProvideOthersInfoSection: display})}
                display={this.state.showProvideOthersInfoSection}>
              <ol className='mdc-typography--body1'>
                <li>
                  <b>Getting started</b>
                  <p>Go to the Google Person Finder homepage by entering the URL (<a href="http://g.co/pf">http://g.co/pf</a>) in the browser and choose the disaster name relevant to you. Then click the [Provide information about someone] button and choose the [Someone else] tab near the top..</p>
                </li>
                <li>
                  <b>Enter the person's name</b>
                  <p>Put the person's name in the [Given name] and [Family name] fields.</p>
                </li>
                <li>
                  <b>Input more detailed information (optional)</b>
                  <p>You can click the [More] button to open up fields for more detailed information, to help others identify the person.</p>
                </li>
                <li>
                  <b>Specify the person's status</b>
                  <p>Select the person's status, a message about their status (e.g., how you know their status), and (optionally) their location.</p>
                </li>
                <li>
                  <b>Submit the record</b>
                  <p>Click [Submit record]. The record will be created.</p>
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
