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

class LatLng {
  constructor(lat, lng) {
    this.lat = lat;
    this.lng = lng;
  }
}

class Bounds {
  constructor() {
    // TODO(nworden): see if there's a better way to do this. seems like there
    // should be.
    this.contains = jest.fn();
  }
}

const constructedMaps = [];

function clearConstructedMaps() {
  constructedMaps.splice(0, constructedMaps.length);
}

class Map {
  constructor(node, settings) {
    this.node = node;
    this.settings = settings;
    constructedMaps.push(this);
    this.addListener = jest.fn();
    this.panTo = jest.fn();
    this.getBounds = jest.fn();
  }
}

const constructedMarkers = [];

function clearConstructedMarkers() {
  constructedMarkers.splice(0, constructedMarkers.length);
}

class Marker {
  constructor(settings) {
    this.settings = settings;
    constructedMarkers.push(this);
    this.setPosition = jest.fn();
  }
}

const mockGoogle = {
  maps: {
    LatLng: LatLng,
    Map: Map,
    Marker: Marker,
    event: {
      trigger: jest.fn(),
    },
  },
};

export {
  mockGoogle,
  Bounds,
  constructedMaps,
  clearConstructedMaps,
  constructedMarkers,
  clearConstructedMarkers
};
