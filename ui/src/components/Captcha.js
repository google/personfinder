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
import Button from '@material/react-button';

const MESSAGES = defineMessages({
  proceed: {
    id: 'RepoHeader.proceed',
    defaultMessage: 'Proceed',
    description: ('Label on a button that a user should click after completing '
        + 'a reCaptcha form.'),
  },
});

class Captcha extends Component {
  constructor(props) {
    super(props);
    this.handleSubmit = this.handleSubmit.bind(this);
  }

  componentDidMount() {
    grecaptcha.render('recaptcha_container', {'sitekey': ENV.recaptcha_key});
  }

  render() {
    return (
      <div className='captcha_wrapper'>
        <form onSubmit={this.handleSubmit}>
          <div id='recaptcha_container'></div>
          <br/>
          <Button
              className='pf-button-primary'
              type='submit'>
            {this.props.intl.formatMessage(MESSAGES.proceed)}
          </Button>
        </form>
      </div>
    );
  }

  handleSubmit(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    this.props.callback(formData.get('g-recaptcha-response'));
  }
}

export default injectIntl(Captcha);
