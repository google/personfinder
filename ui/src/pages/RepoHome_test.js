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

import RepoHome from './RepoHome';
import RepoHeader from '../components/RepoHeader';
import SearchBar from '../components/SearchBar';
import {mountWithIntl} from '../testing/enzyme-intl-helper';
import {flushPromises} from '../testing/utils';

Enzyme.configure({adapter: new Adapter()});

const REPO_DATA = {repoId: 'albany', title: 'Albany', recordCount: 100,};

function setupPageWrapper() {
  fetch.mockResponseOnce(JSON.stringify(REPO_DATA));
  const history = createMemoryHistory('/albany');
  const matchValue = {params: {repoId: 'albany'}};
  const wrapper = mountWithIntl(
    <MemoryRouter>
      <RepoHome history={history} match={matchValue} />
    </MemoryRouter>
  );
  return [wrapper, history];
}

describe('testing RepoHome', () => {
  beforeEach(() => {
    fetch.resetMocks();
  });

  test('RepoHeader configured correctly', () => {
    const [wrapper] = setupPageWrapper();
    return flushPromises().then(() => {
      wrapper.update();
      const actualRepoHeader = wrapper.find(RepoHeader).get(0);
      expect(actualRepoHeader.props.repo).toEqual(REPO_DATA);
      expect(actualRepoHeader.props.backButtonTarget).toBe('/');
      wrapper.unmount();
    });
  });

  test('SearchBar configured correctly', () => {
    const [wrapper, history] = setupPageWrapper();
    return flushPromises().then(() => {
      wrapper.update();
      const actualSearchBar = wrapper.find(SearchBar).get(0);
      expect(actualSearchBar.props.repoId).toBe('albany');
      expect(actualSearchBar.props.initialValue).toBe('');
      actualSearchBar.props.onSearch('thátcher');
      expect(history.entries[1].pathname).toBe('/albany/results');
      expect(history.entries[1].search).toBe('?query_name=th%C3%A1tcher');
      wrapper.unmount();
    });
  });

  test('"Provide info" button goes to create page', () => {
    const [wrapper, history] = setupPageWrapper();
    return flushPromises().then(() => {
      wrapper.update();
      wrapper.find('.pf-button-secondary').at(0).simulate('click');
      expect(history.entries[1].pathname).toBe('/albany/create');
      wrapper.unmount();
    });
  });

  test('snapshot test for RepoHome', () => {
    // We don't use setupPageWrapper here because we need to avoid passing
    // a history object: it will generate random keys that mess up the
    // snapshot.
    fetch.mockResponseOnce(JSON.stringify(REPO_DATA));
    const matchValue = {params: {repoId: 'albany'}};
    const wrapper = mountWithIntl(
      <MemoryRouter>
        <RepoHome match={matchValue} />
      </MemoryRouter>
    );
    return flushPromises().then(() => {
      wrapper.update();
      expect(toJson(wrapper.find(RepoHome).at(0))).toMatchSnapshot();
      wrapper.unmount();
    });
  });
});
