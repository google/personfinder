import Enzyme from 'enzyme';
import Adapter from 'enzyme-adapter-react-16';
import React from 'react';

import Footer from './Footer';
import {mountWithIntl} from '../testing/enzyme-intl-helper';

Enzyme.configure({adapter: new Adapter()});

test('footer should contain "PLEASE NOTE"', () => {
  const wrapper = mountWithIntl(
    <Footer />
  );
  expect(wrapper.find('span').text()).toMatch(/PLEASE NOTE/);
  wrapper.unmount();
});
