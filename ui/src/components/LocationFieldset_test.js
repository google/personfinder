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


import toJson from 'enzyme-to-json';

import Enzyme from 'enzyme';
import Adapter from 'enzyme-adapter-react-16';
import React from 'react';

import LocationFieldset from './LocationFieldset';
import {mountWithIntl} from '../testing/enzyme-intl-helper';

Enzyme.configure({adapter: new Adapter()});

test('location text should be populated from props', () => {
  global.ENV = {};
  const wrapper = mountWithIntl(
    <LocationFieldset
        locationText='burlington, vt' />
  );
  wrapper.update();
  expect(wrapper.find('Input').get(0).props.value).toBe('burlington, vt');
  wrapper.unmount();
});

test('location text update should call back', () => {
  global.ENV = {};
  const mockLocationTextUpdateCallback = jest.fn();
  const wrapper = mountWithIntl(
    <LocationFieldset
        onLocationTextUpdate={mockLocationTextUpdateCallback} />
  );
  const changeEvent = {target: {value: 'burlington, vt'}};
  wrapper.find('Input').simulate('change', changeEvent);
  wrapper.update();
  expect(mockLocationTextUpdateCallback).toHaveBeenCalledWith('burlington, vt');
  wrapper.unmount();
});

test('no map button present without Maps API key', () => {
  global.ENV = {};
  const wrapper = mountWithIntl(<LocationFieldset />);
  wrapper.update();
  expect(wrapper.find('button').length).toBe(1);
  wrapper.unmount();
});

test('no map button present with empty Maps API key', () => {
  global.ENV = {'maps_api_key': ''};
  const wrapper = mountWithIntl(<LocationFieldset />);
  wrapper.update();
  expect(wrapper.find('button').length).toBe(1);
  wrapper.unmount();
});

test('map button present with Maps API key', () => {
  global.ENV = {'maps_api_key': 'oto4tjwjp4'};
  const wrapper = mountWithIntl(<LocationFieldset />);
  wrapper.update();
  expect(wrapper.find('button').length).toBe(2);
  wrapper.unmount();
});
