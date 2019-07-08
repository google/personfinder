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

import React, {Component} from 'react';
import ReactDOM from 'react-dom';
import {FormattedHTMLMessage, FormattedMessage, defineMessages, injectIntl} from 'react-intl';
import {withRouter} from 'react-router-dom';
import Button from '@material/react-button';
import {Chip} from '@material/react-chips';
import TextField, {HelperText, Input} from '@material/react-text-field';
import Utils from './../utils/Utils';

const MESSAGES = defineMessages({
  hideMap: {
    id: 'LocationFieldset.hideMap',
    defaultMessage: 'Hide map',
    description: 'Label on a button to hide a map display.',
  },
  lastKnownLocation: {
    id: 'LocationFieldset.lastKnownLocation',
    defaultMessage: 'Last known location',
    description: ('A label on a form field for the last known location of a '
        + 'person.'),
  },
  lastKnownLocationInstructions: {
    id: 'LocationFieldset.lastKnownLocationInstructions',
    defaultMessage: ('Type an address or open the map to indicate the location '
        + 'by clicking on the map.'),
    description: ('Instructions for how to fill in a field indicating the last '
        + 'known location of a person.'),
  },
  showMap: {
    id: 'LocationFieldset.showMap',
    defaultMessage: 'Show map',
    description: 'Label on a button to show a map.',
  },
  useLocation: {
    id: 'LocationFieldset.useLocation',
    defaultMessage: 'Use location',
    description: ('Label on a button that a user can use to automatically fill '
        + 'in a location field with their browser location.'),
  },
});

const BASE_MAPS_API_URL = 'https://maps.googleapis.com/maps/api/js';

class LocationFieldset extends Component {
  constructor(props) {
    super(props);
    this.state = {
      showMap: false,
      haveStartedLoadingMapScript: false,
      haveFinishedLoadingMapScript: false,
    };
    this.mapsApiEnabled = Boolean(ENV.maps_api_key);
    this.onLocationLatLngUpdate = this.onLocationLatLngUpdate.bind(this);
  }

  componentDidUpdate(prevProps, prevState) {
    // This is more complex than I'd like, but basically what's going on is I
    // want to ensure the Google Maps JS is never loaded more than once, and
    // only loaded at all if the user wants to show the map.
    // The first time showMap is set to true, we also set
    // haveStartedLoadingMapScript to true, and when that's set to true we load
    // the map script.
    if (this.state.showMap && !prevState.showMap) {
      this.setState({haveStartedLoadingMapScript: true});
    } else if (this.state.haveStartedLoadingMapScript &&
        !prevState.haveStartedLoadingMapScript) {
      Utils.loadExternalScript(
        BASE_MAPS_API_URL + '?key=' + ENV.maps_api_key,
        () => this.setState({haveFinishedLoadingMapScript: true}));
    }
  }

  onLocationLatLngUpdate(value) {
    const textValue = value[0] + ', ' + value[1];
    this.props.onLocationLatLngUpdate(value);
    this.props.onLocationTextUpdate(textValue);
  }

  onLocationTextFieldBlur(e) {
    if (this.state.haveFinishedLoadingMapScript) {
      const geocoder = new google.maps.Geocoder();
      geocoder.geocode(
          {address: this.props.locationText},
          (results, status) => {
            if ((status != 'OK') || (results.length == 0)) {
              // We're geocoding strictly on a best-effort basis.
              return;
            }
            const resultGeoLocation = results[0].geometry.location;
            this.props.onLocationLatLngUpdate(
                [resultGeoLocation.lat(), resultGeoLocation.lng()]);
          });
    }
  }

  render() {
    let showHideMapButton = null;
    if (this.mapsApiEnabled) {
      const newMapState = !this.state.showMap;
      const showHideMapButtonLabel =
          newMapState ?
          this.props.intl.formatMessage(MESSAGES.showMap) :
          this.props.intl.formatMessage(MESSAGES.hideMap);
      showHideMapButton = (
          <Chip
              className='locationfieldset-showmap'
              label={
                <div className='locationfieldset-showmap-label'>
                  <img src='/static/icons/maticon_map.svg' />
                  &nbsp;
                  {showHideMapButtonLabel}
                </div>
              }
              handleInteraction={() => this.setState({showMap: newMapState})} />
      );
    }
    const map = (this.state.showMap && this.state.haveFinishedLoadingMapScript)
        ? <MapDisplay
            mapDefaultCenter={this.props.mapDefaultCenter}
            mapDefaultZoom={this.props.mapDefaultZoom}
            pinLocation={this.props.locationLatLng}
            onLocationTextUpdate={this.props.onLocationTextUpdate}
            onLocationLatLngUpdate={this.onLocationLatLngUpdate} />
        : null;
    return (
      <div>
        <TextField
          label={this.props.intl.formatMessage(MESSAGES.lastKnownLocation)}
          outlined
          textarea
        >
          <Input
            name='last_known_location'
            id='forminput-lastknownlocation'
            value={this.props.locationText}
            onChange={(e) => this.props.onLocationTextUpdate(e.target.value)}
            onBlur={(e) => this.onLocationTextFieldBlur(e)} />
        </TextField>
        <p className='mdc-typography--body1 form-explanationtext'>
          <FormattedHTMLMessage {...MESSAGES.lastKnownLocationInstructions} />
        </p>
        <Chip
            className='locationfieldset-uselocation'
            label={
              <div className='locationfieldset-uselocation-label'>
                <img src='/static/icons/maticon_my_location.svg' />
                &nbsp;
                <FormattedMessage {...MESSAGES.useLocation} />
              </div>
            }
            handleInteraction={
              () => this.populateLocationWithCurrentLocation()} />
        &nbsp;
        {showHideMapButton}
        {map}
      </div>
    );
  }

  populateLocationWithCurrentLocation() {
    navigator.geolocation.getCurrentPosition((position) =>
      this.onLocationLatLngUpdate(
          [position.coords.latitude, position.coords.longitude]));
  }
}

class MapDisplayImpl extends Component {
  constructor(props) {
    super(props);
  }

  componentDidMount() {
    // We can't do this in the constructor because we need it to render first,
    // or else the div it looks for won't be present yet.
    this.loadMap();
  }

  componentDidUpdate(prevProps, prevState) {
    if (this.props.pinLocation != prevProps.pinLocation) {
      if (this.marker) {
        const pinLocation = this.props.pinLocation
            || this.props.mapDefaultCenter;
        const pinLatLng = new google.maps.LatLng(
            pinLocation[0], pinLocation[1]);
        this.marker.setPosition(pinLatLng);
        if (!this.map.getBounds().contains(pinLatLng)) {
          this.map.panTo(pinLatLng);
        }
      }
    }
  }

  loadMap() {
    const mapNode = ReactDOM.findDOMNode(this.refs.map);
    const pinLocation = this.props.pinLocation
        || this.props.mapDefaultCenter;
    const pinLatLng = new google.maps.LatLng(pinLocation[0], pinLocation[1]);
    this.map = new google.maps.Map(mapNode, {
      center: {lat: this.props.mapDefaultCenter[0],
               lng: this.props.mapDefaultCenter[1]},
      zoom: this.props.mapDefaultZoom,
    });
    this.marker = new google.maps.Marker({
      map: this.map,
      position: pinLatLng,
    });
    this.map.addListener('click', (e) => this.props.onLocationLatLngUpdate(
        [e.latLng.lat(), e.latLng.lng()]));
    google.maps.event.trigger(this.map, 'ready');
  }

  render() {
    const mapStyle = {
      height: '250px',
      width: '100%',
    };
    // The Maps API will replace the contents of this div once the map loads.
    return (
      <div ref='map' style={mapStyle}>
        Map is loading
      </div>
    );
  }
}

const MapDisplay = injectIntl(MapDisplayImpl);

export default injectIntl(LocationFieldset);
