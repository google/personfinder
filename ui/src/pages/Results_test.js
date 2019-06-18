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

import Results from './Results';
import RepoHeader from '../components/RepoHeader';
import SearchBar from '../components/SearchBar';
import {mountWithIntl} from '../testing/enzyme-intl-helper';
import {flushPromises} from '../testing/utils';

Enzyme.configure({adapter: new Adapter()});

const REPO_DATA = {repoId: 'albany', title: 'Albany', recordCount: 100,};
const RESULTS_DATA = [
    {
      personId: '123',
      fullNames: ['Fred Fredricks'],
      alternateNames: ['Freddy'],
      timestampType: 'creation',
      timestamp: '2019-05-15T17:12:23.936282Z',
      localPhotoUrl: null,
    },
    {
      personId: '321',
      fullNames: ['Alan Smith', 'Alan Herbert Smith'],
      alternateNames: [],
      timestampType: 'update',
      timestamp: '2019-05-16T16:35:23.936282Z',
      localPhotoUrl: 'http://www.example.com/notevenreallylocal.jpg',
    },
  ]

function setupPageWrapper() {
  fetch.mockResponseOnce(JSON.stringify(REPO_DATA));
  fetch.mockResponseOnce(JSON.stringify(RESULTS_DATA));
  const history = createMemoryHistory('/albany');
  const locationValue = {search: 'query_name=th%C3%A1tcher'};
  const matchValue = {params: {repoId: 'albany'}};
  const wrapper = mountWithIntl(
    <MemoryRouter>
      <Results
          history={history}
          location={locationValue}
          match={matchValue} />
    </MemoryRouter>
  );
  return [wrapper, history];
}

describe('testing Results', () => {
  beforeEach(() => {
    fetch.resetMocks();
  });

  test('Results calls to correct API URLs', () => {
    const [wrapper] = setupPageWrapper();
    return flushPromises().then(() => {
      wrapper.update();
      expect(fetch.mock.calls.length).toBe(2);
      expect(fetch.mock.calls[0][0]).toBe('/albany/d/repo');
      expect(fetch.mock.calls[1][0]).toBe(
          '/albany/d/results?query=th%C3%A1tcher');
      wrapper.unmount();
    });
  });

  test('RepoHeader configured correctly', () => {
    const [wrapper] = setupPageWrapper();
    return flushPromises().then(() => {
      wrapper.update();
      const actualRepoHeader = wrapper.find(RepoHeader).get(0);
      expect(actualRepoHeader.props.repo).toEqual(REPO_DATA);
      expect(actualRepoHeader.props.backButtonTarget).toBe('/albany');
      wrapper.unmount();
    });
  });

  test('SearchBar configured correctly', () => {
    const [wrapper, history] = setupPageWrapper();
    return flushPromises().then(() => {
      wrapper.update();
      const actualSearchBar = wrapper.find(SearchBar).get(0);
      expect(actualSearchBar.props.repoId).toBe('albany');
      expect(actualSearchBar.props.initialValue).toBe('thátcher');
      actualSearchBar.props.onSearch('fródo');
      expect(history.entries[1].pathname).toBe('/albany/results');
      expect(history.entries[1].search).toBe('?query_name=fr%C3%B3do');
      wrapper.unmount();
    });
  });

  test('"Add Person" FAB points to create page', () => {
    const [wrapper, history] = setupPageWrapper();
    return flushPromises().then(() => {
      wrapper.update();
      wrapper.find('.results-addfab').at(0).simulate('click');
      expect(history.entries[1].pathname).toBe('/albany/create');
      wrapper.unmount();
    });
  });

  test('snapshot test for Results', () => {
    // We don't use setupPageWrapper here because we want to avoid passing a
    // history object and need to specify initialEntries, to avoid generating
    // random keys that mess up the snapshot.
    fetch.mockResponseOnce(JSON.stringify(REPO_DATA));
    fetch.mockResponseOnce(JSON.stringify(RESULTS_DATA));
    const locationValue = {search: 'query_name=th%C3%A1tcher'};
    const matchValue = {params: {repoId: 'albany'}};
    const wrapper = mountWithIntl(
      <MemoryRouter
          initialEntries={[{pathname: '/albany/results', key: 'abc123'}]}>
        <Results
            location={locationValue}
            match={matchValue} />
      </MemoryRouter>
    );
    return flushPromises().then(() => {
      wrapper.update();
      expect(toJson(wrapper.find(Results).at(0))).toMatchSnapshot();
      wrapper.unmount();
    });
  });
});
