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
import Utils from './../utils/Utils';

const MESSAGES = defineMessages({
  captchaToolLoading: {
    id: 'Captcha.captchaToolLoading',
    defaultMessage: 'Captcha tool loading...',
    description: ('A message shown while the captcha JavaScript tool is '
        + 'loading.'),
  },
});

class Captcha extends Component {
  constructor(props) {
    super(props);
    this.state = {
      scriptHasLoaded: false,
    };
  }

  componentDidMount() {
    Utils.loadExternalScript(
        'https://www.google.com/recaptcha/api.js?render=explicit',
        () => grecaptcha.ready(() => {
            grecaptcha.render(
              'recaptcha_container', {
                'callback': this.props.callback,
                'sitekey': ENV.recaptcha_site_key,
              });
            this.setState({scriptHasLoaded: true});
        }));
  }

  render() {
    return (
      <div className='captcha_wrapper'>
        {this.state.scriptHasLoaded ? null :
           <FormattedMessage {...MESSAGES.captchaToolLoading} />}
        <div id='recaptcha_container'></div>
      </div>
    );
  }
}

export default injectIntl(Captcha);
