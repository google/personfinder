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

import Zippy from './Zippy';
import {mountWithIntl} from '../testing/enzyme-intl-helper';

Enzyme.configure({adapter: new Adapter()});

test('content should not show when zippy is closed', () => {
  const wrapper = mountWithIntl(
      <Zippy
          display={false}
          header={'Header text'}>
        Child content
      </Zippy>
  );
  expect(wrapper.text()).toStrictEqual('Header text');
});

test('content should show when zippy is open', () => {
  const wrapper = mountWithIntl(
      <Zippy
          display={true}
          header={'Header text'}>
        Child content
      </Zippy>
  );
  expect(wrapper.text()).toStrictEqual('Header textChild content');
});

test('zippy should call callback when opened', () => {
  const mockZipHandler = jest.fn();
  const wrapper = mountWithIntl(
      <Zippy
          zipHandler={mockZipHandler}
          display={false}
          header={'Header text'}>
        Child content
      </Zippy>
  );
  wrapper.find('a').simulate('click');
  expect(mockZipHandler).toHaveBeenCalledWith(true);
});

test('zippy should call callback when closed', () => {
  const mockZipHandler = jest.fn();
  const wrapper = mountWithIntl(
      <Zippy
          zipHandler={mockZipHandler}
          display={true}
          header={'Header text'}>
        Child content
      </Zippy>
  );
  wrapper.find('a').simulate('click');
  expect(mockZipHandler).toHaveBeenCalledWith(false);
});
