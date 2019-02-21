import Enzyme from 'enzyme';
import Adapter from 'enzyme-adapter-react-16';
import React from 'react';

import LoadingIndicator from './LoadingIndicator';
import {mountWithIntl} from '../testing/enzyme-intl-helper';

Enzyme.configure({adapter: new Adapter()});

test('loading indicator should say loading', () => {
  const wrapper = mountWithIntl(
    <LoadingIndicator />
  );
  expect(wrapper.find('span').text()).toBe('Loading...');
  wrapper.unmount();
});
