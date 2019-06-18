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

const MESSAGES = defineMessages({
  helpDocument: {
    id: 'HowToPage.helpDocument',
    defaultMessage: 'Help document',
    description: 'A header for a page with help documentation.',
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
const HowToPage = (props) => (
  <StaticPageWrapper
      pageTitle={props.intl.formatMessage(MESSAGES.helpDocument)}>
    <h2 className='mdc-typography--subtitle2'><FormattedMessage {...MESSAGES.pfUserGuide} /></h2>
    <p className='mdc-typography--body1'>Person Finder can be used by anyone from a PC or mobile phone. This document shows how to provide and search for safety information in emergency situations.</p>
  </StaticPageWrapper>
);

export default injectIntl(HowToPage);
