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

import SearchBar from './SearchBar';
import {mountWithIntl} from '../testing/enzyme-intl-helper';

Enzyme.configure({adapter: new Adapter()});

test('value change should update state and MDC Input', () => {
  const wrapper = mountWithIntl(
    <SearchBar />
  );
  const event = {target: {value: 'gilbert'}};
  wrapper.find('Input').simulate('change', event);
  wrapper.update();
  expect(wrapper.find('SearchBar').state().value).toBe('gilbert');
  expect(wrapper.find('Input').get(0).props.value).toBe('gilbert');
  wrapper.unmount();
});

test('search handler should be called on "Enter" keydown', () => {
  const mockSearchCallback = jest.fn();
  const wrapper = mountWithIntl(
    <SearchBar onSearch={mockSearchCallback} />
  );
  const changeEvent = {target: {value: 'gilbert'}};
  wrapper.find('Input').simulate('change', changeEvent);
  wrapper.find('Input').simulate('keydown', {key: 'Enter'});
  wrapper.update();
  expect(mockSearchCallback).toHaveBeenCalledWith('gilbert');
  wrapper.unmount();
});

test('value should update if props change', () => {
  const wrapper = mountWithIntl(
    <SearchBar initialValue='tom' />
  );
  expect(wrapper.find('SearchBar').state().value).toBe('tom');
  wrapper.setProps({initialValue: 'matt'});
  wrapper.update();
  expect(wrapper.find('SearchBar').state().value).toBe('matt');
  wrapper.unmount();
});
