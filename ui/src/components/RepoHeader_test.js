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
