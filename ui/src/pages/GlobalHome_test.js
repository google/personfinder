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
import toJson from 'enzyme-to-json';
import {createMemoryHistory} from 'history';
import React from 'react';
import {MemoryRouter} from 'react-router';

import GlobalHome from './GlobalHome';
import {mountWithIntl} from '../testing/enzyme-intl-helper';
import {flushPromises} from '../testing/utils';

Enzyme.configure({adapter: new Adapter()});

const REPO_DATA = [
    {repoId: 'haiti', title: 'Haiti', recordCount: 400},
    {repoId: 'japan', title: 'Japan', recordCount: 100},
    {repoId: 'albany', title: 'Albany', recordCount: 100},
    {repoId: 'seattle', title: 'Seattle', recordCount: 800},
    {repoId: 'montreal', title: 'Montreal', recordCount: 500},
    {repoId: 'belgium', title: 'Belgium', recordCount: 100},
    {repoId: 'boise', title: 'Boise', recordCount: 100},
];

function setupPageWrapper() {
  fetch.mockResponseOnce(JSON.stringify(REPO_DATA));
  const history = createMemoryHistory('/');
  const wrapper = mountWithIntl(
    <MemoryRouter>
      <GlobalHome history={history} />
    </MemoryRouter>
  );
  return [wrapper, history];
}

describe('testing GlobalHome', () => {
  beforeEach(() => {
    fetch.resetMocks();
  });

  test('repo cards are rendered', () => {
    const [wrapper] = setupPageWrapper();
    return flushPromises().then(() => {
      wrapper.update();
      const repoCardTitles = wrapper.find('h5.repocard-title');
      expect(repoCardTitles.length).toBe(7);
      const expectedTitles = [
          'Haiti', 'Japan', 'Albany', 'Seattle', 'Montreal', 'Belgium',
          'Boise'];
      for (let i = 0; i < expectedTitles.length; i++) {
        expect(repoCardTitles.at(i).text()).toBe(expectedTitles[i]);
      }
      wrapper.unmount();
    });
  });

  test('assigns display categories to repos', () => {
    const [wrapper] = setupPageWrapper();
    return flushPromises().then(() => {
      wrapper.update();
      const expectedDisplayCategories = [0, 1, 2, 3, 4, 0, 1];
      for (let i = 0; i < expectedDisplayCategories.length; i++) {
        expect(wrapper.find('GlobalHome').state().repos[i].displayCategory)
            .toBe(expectedDisplayCategories[i]);
      }
      wrapper.unmount();
    });
  });

  test('repo cards point to the right place', () => {
    const [wrapper, history] = setupPageWrapper();
    return flushPromises().then(() => {
      wrapper.update();
      const repoCardImages = wrapper.find('.repocard-image');
      expect(repoCardImages.length).toBe(7);
      repoCardImages.at(1).simulate('click');
      expect(history.entries.length).toBe(2);
      expect(history.entries[1].pathname).toBe('/japan');
      wrapper.unmount();
    });
  });

  test('snapshot test for GlobalHome', () => {
    // We don't use setupPageWrapper here because we need to avoid passing
    // a history object: it will generate random keys that mess up the
    // snapshot.
    fetch.mockResponseOnce(JSON.stringify(REPO_DATA));
    const wrapper = mountWithIntl(
      <MemoryRouter>
        <GlobalHome />
      </MemoryRouter>
    );
    return flushPromises().then(() => {
      wrapper.update();
      expect(toJson(wrapper.find(GlobalHome).at(0))).toMatchSnapshot();
      wrapper.unmount();
    });
  });
});
