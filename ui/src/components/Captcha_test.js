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


import Enzyme from 'enzyme';
import Adapter from 'enzyme-adapter-react-16';
import React from 'react';

import Captcha from './Captcha';
import {mountWithIntl} from '../testing/enzyme-intl-helper';
import Utils from './../utils/Utils';

Enzyme.configure({adapter: new Adapter()});

let mockLoadExternalScript;

describe('testing Captcha', () => {
  beforeEach(() => {
    global.ENV = {
      'recaptcha_site_key': 'abc123',
    };
    jest.mock('./../utils/Utils');
    mockLoadExternalScript = jest.fn();
    Utils.loadExternalScript = mockLoadExternalScript.bind(Utils);
    const mockGRecaptcha = {
      ready: jest.fn(),
      render: jest.fn(),
    };
    global.grecaptcha = mockGRecaptcha;
  });

  test('captcha loads correctly', () => {
    const mockCallback = jest.fn();
    const wrapper = mountWithIntl(<Captcha callback={mockCallback} />);
    wrapper.update();
    // Check that the external script loader was called, then call the callback
    // passed to it (pulled from the list of arguments mockLoadExternalScript
    // was called with).
    expect(mockLoadExternalScript).toHaveBeenCalledWith(
        'https://www.google.com/recaptcha/api.js?render=explicit',
        expect.anything());
    mockLoadExternalScript.mock.calls[0][1]();
    // Check that grecaptcha.ready was called, then call the callback passed to
    // it.
    expect(global.grecaptcha.ready).toHaveBeenCalled();
    global.grecaptcha.ready.mock.calls[0][0]();
    // Finally, check that grecaptcha.render was called and the loading message
    // is absent.
    expect(global.grecaptcha.render).toHaveBeenCalledWith(
        'recaptcha_container', {
          'callback': mockCallback,
          'sitekey': 'abc123',
        });
    expect(wrapper.text()).not.toMatch(/Captcha tool loading/);
    wrapper.unmount();
  });

  test('shows loading message before the script loads', () => {
    const wrapper = mountWithIntl(<Captcha />);
    wrapper.update();
    expect(wrapper.text()).toMatch(/Captcha tool loading/);
    wrapper.unmount();
  });
});
