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
import {MemoryRouter} from 'react-router';

import RepoHeader from './RepoHeader';
import {mountWithIntl} from '../testing/enzyme-intl-helper';

Enzyme.configure({adapter: new Adapter()});

test('repo header should have product name and repo title', () => {
  const wrapper = mountWithIntl(
    <MemoryRouter>
      <RepoHeader repo={{title: 'Aliens'}} backButtonTarget='/notused' />
    </MemoryRouter>
  );
  expect(wrapper.find('p.mdc-typography--subtitle1').text())
      .toBe('Google Person Finder');
  expect(wrapper.find('p.mdc-typography--subtitle2').text()).toBe('Aliens');
  wrapper.unmount();
});

test('repo header back button should point where specified', () => {
  const wrapper = mountWithIntl(
    <MemoryRouter>
      <RepoHeader repo={{title: 'Aliens'}} backButtonTarget='/homepage' />
    </MemoryRouter>
  );
  expect(wrapper.find('Link').props().to).toBe('/homepage');
  wrapper.unmount();
});
