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
