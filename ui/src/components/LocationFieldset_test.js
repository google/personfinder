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

import LocationFieldset, {MapDisplay} from './LocationFieldset';
import {mountWithIntl} from '../testing/enzyme-intl-helper';
import {
  mockGoogle,
  Bounds,
  constructedMaps,
  clearConstructedMaps,
  constructedMarkers,
  clearConstructedMarkers,
} from '../testing/mock-google-module';
import Utils from './../utils/Utils';

Enzyme.configure({adapter: new Adapter()});

let mockLoadExternalScript;

function showMap(wrapper) {
  wrapper.find('div.locationfieldset-showmap').at(0).simulate('click');
  mockLoadExternalScript.mock.calls[0][1]();
  wrapper.update();
}

describe('testing LocationFieldset', () => {
  beforeEach(() => {
    global.ENV = {
      'maps_api_key': 'abc123',
    };
    jest.mock('./../utils/Utils');
    mockLoadExternalScript = jest.fn();
    Utils.loadExternalScript = mockLoadExternalScript.bind(Utils);
    global.google = mockGoogle;
  });

  afterEach(() => {
    clearConstructedMaps();
    clearConstructedMarkers();
  });

  test('location text should be populated from props', () => {
    const wrapper = mountWithIntl(
      <LocationFieldset
          mapDefaultCenter={[40.6782, -73.9442]}
          mapDefaultZoom={10}
          locationText='burlington, vt' />
    );
    wrapper.update();
    expect(wrapper.find('Input').get(0).props.value).toBe('burlington, vt');
    wrapper.unmount();
  });

  test('location text update should call back', () => {
    const mockLocationTextUpdateCallback = jest.fn();
    const wrapper = mountWithIntl(
      <LocationFieldset
          mapDefaultCenter={[40.6782, -73.9442]}
          mapDefaultZoom={10}
          onLocationTextUpdate={mockLocationTextUpdateCallback} />
    );
    const changeEvent = {target: {value: 'burlington, vt'}};
    wrapper.find('Input').simulate('change', changeEvent);
    wrapper.update();
    expect(mockLocationTextUpdateCallback).toHaveBeenCalledWith(
        'burlington, vt');
    wrapper.unmount();
  });

  test('no map button present without Maps API key', () => {
    global.ENV = {};
    const wrapper = mountWithIntl(
        <LocationFieldset
            mapDefaultCenter={[40.6782, -73.9442]}
            mapDefaultZoom={10}
            />);
    wrapper.update();
    expect(wrapper.find('div.locationfieldset-showmap').length).toBe(0);
    wrapper.unmount();
  });

  test('no map button present with empty Maps API key', () => {
    global.ENV = {'maps_api_key': ''};
    const wrapper = mountWithIntl(
        <LocationFieldset
            mapDefaultCenter={[40.6782, -73.9442]}
            mapDefaultZoom={10}
            />);
    wrapper.update();
    expect(wrapper.find('div.locationfieldset-showmap').length).toBe(0);
    wrapper.unmount();
  });

  test('map button present with Maps API key', () => {
    const wrapper = mountWithIntl(
        <LocationFieldset
            mapDefaultCenter={[40.6782, -73.9442]}
            mapDefaultZoom={10}
            />);
    wrapper.update();
    expect(wrapper.find('div.locationfieldset-showmap').length).toBe(1);
    expect(wrapper.find('div.locationfieldset-showmap').text()).toContain(
        'Show map');
    wrapper.unmount();
  });

  test('map script is loaded on show map button click', () => {
    const wrapper = mountWithIntl(
        <LocationFieldset
            mapDefaultCenter={[40.6782, -73.9442]}
            mapDefaultZoom={10}
            />);
    wrapper.update();
    wrapper.find('div.locationfieldset-showmap').at(0).simulate('click');
    expect(mockLoadExternalScript).toHaveBeenCalledWith(
        'https://maps.googleapis.com/maps/api/js?key=abc123',
        expect.anything());
    wrapper.unmount();
  });

  test('map script is only loaded once', () => {
    const wrapper = mountWithIntl(
        <LocationFieldset
            mapDefaultCenter={[40.6782, -73.9442]}
            mapDefaultZoom={10}
            />);
    wrapper.update();
    // Show the map, hide it, and show it again.
    wrapper.find('div.locationfieldset-showmap').at(0).simulate('click');
    wrapper.find('div.locationfieldset-showmap').at(0).simulate('click');
    wrapper.find('div.locationfieldset-showmap').at(0).simulate('click');
    expect(mockLoadExternalScript).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  test('map is displayed on show map button click', () => {
    const wrapper = mountWithIntl(
        <LocationFieldset
            mapDefaultCenter={[40.6782, -73.9442]}
            mapDefaultZoom={10}
            />);
    wrapper.update();
    showMap(wrapper);
    expect(wrapper.find('MapDisplayImpl').length).toBe(1);
    expect(wrapper.find('div.locationfieldset-showmap').at(0).text()).toContain(
        'Hide map');
    wrapper.unmount();
  });

  test('lat/lng update should call back', () => {
    const mockLocationTextUpdateCallback = jest.fn();
    const mockLocationLatLngUpdateCallback = jest.fn();
    const wrapper = mountWithIntl(
        <LocationFieldset
            mapDefaultCenter={[40.6782, -73.9442]}
            mapDefaultZoom={10}
            onLocationTextUpdate={mockLocationTextUpdateCallback}
            onLocationLatLngUpdate={mockLocationLatLngUpdateCallback} />);
    wrapper.update();
    showMap(wrapper);
    // Calling the function passed into the Map should cause the
    // LocationFieldset to propagate the data up.
    wrapper.find('MapDisplayImpl').prop('onLocationLatLngUpdate')(
        [35.6762, 139.6503]);
    expect(mockLocationTextUpdateCallback).toHaveBeenCalledWith(
        '35.6762, 139.6503');
    expect(mockLocationLatLngUpdateCallback).toHaveBeenCalledWith(
        [35.6762, 139.6503]);
  });

  test('populate with current location', () => {
    const mockGetCurrentPosition = jest.fn();
    global.navigator.geolocation = {getCurrentPosition: mockGetCurrentPosition};
    const mockLocationTextUpdateCallback = jest.fn();
    const mockLocationLatLngUpdateCallback = jest.fn();
    const wrapper = mountWithIntl(
        <LocationFieldset
            mapDefaultCenter={[40.6782, -73.9442]}
            mapDefaultZoom={10}
            onLocationTextUpdate={mockLocationTextUpdateCallback}
            onLocationLatLngUpdate={mockLocationLatLngUpdateCallback} />);
    wrapper.update();
    wrapper.find('div.locationfieldset-uselocation').at(0).simulate('click');
    mockGetCurrentPosition.mock.calls[0][0](
        {coords: {latitude: 29.7604, longitude: -95.3698}});
    expect(mockLocationTextUpdateCallback).toHaveBeenCalledWith(
        '29.7604, -95.3698');
    expect(mockLocationLatLngUpdateCallback).toHaveBeenCalledWith(
        [29.7604, -95.3698]);
  });

  test('map loads correctly', () => {
    const wrapper = mountWithIntl(
        <LocationFieldset
            mapDefaultCenter={[40.6782, -73.9442]}
            mapDefaultZoom={10}
            />);
    wrapper.update();
    showMap(wrapper);
    expect(global.google.maps.event.trigger).toHaveBeenCalledWith(
        expect.any(global.google.maps.Map), 'ready');
    const map = global.google.maps.event.trigger.mock.calls[0][0];
    expect(map.settings).toStrictEqual({
        center: {lat: 40.6782, lng: -73.9442},
        zoom: 10,
    });
    expect(constructedMarkers.length).toBe(1);
    expect(constructedMarkers[0].settings.position.lat).toBe(40.6782);
    expect(constructedMarkers[0].settings.position.lng).toBe(-73.9442);
    wrapper.unmount();
  });

  test('map marker updates on lat/lng change', () => {
    const wrapper = mountWithIntl(
        <LocationFieldset
            mapDefaultCenter={[40.6782, -73.9442]}
            mapDefaultZoom={10}
            />);
    wrapper.update();
    showMap(wrapper);
    const map = constructedMaps[0];
    const bounds = new Bounds();
    bounds.contains.mockReturnValue(true);
    map.getBounds.mockReturnValue(bounds);
    wrapper.setProps({locationLatLng: [46.8772, -96.7898]});
    const newLatLng = constructedMarkers[0].setPosition.mock.calls[0][0];
    expect(newLatLng.lat).toBe(46.8772);
    expect(newLatLng.lng).toBe(-96.7898);
    expect(map.panTo).toHaveBeenCalledTimes(0);
    wrapper.unmount();
  });

  test('map pans when given out-of-bounds location', () => {
    const wrapper = mountWithIntl(
        <LocationFieldset
            mapDefaultCenter={[40.6782, -73.9442]}
            mapDefaultZoom={10}
            />);
    wrapper.update();
    showMap(wrapper);
    const map = constructedMaps[0];
    const bounds = new Bounds();
    bounds.contains.mockReturnValue(false);
    map.getBounds.mockReturnValue(bounds);
    wrapper.setProps({locationLatLng: [39.7392, -104.9903]});
    const pannedToLatLng = map.panTo.mock.calls[0][0];
    expect(pannedToLatLng.lat).toBe(39.7392);
    expect(pannedToLatLng.lng).toBe(-104.9903);
    wrapper.unmount();
  });
});
