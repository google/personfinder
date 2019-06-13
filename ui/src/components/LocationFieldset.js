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
import {defineMessages, injectIntl} from 'react-intl';
import {withRouter} from 'react-router-dom';
import Button from '@material/react-button';
import TextField, {HelperText, Input} from '@material/react-text-field';

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
  showMap: {
    id: 'LocationFieldset.showMap',
    defaultMessage: 'Show map',
    description: 'Label on a button to show a map.',
  },
});

const BASE_MAPS_API_URL = 'https://maps.googleapis.com/maps/api/js';

class LocationFieldset extends Component {
  constructor(props) {
    super(props);
    this.state = {
      markerLocation: null,
      selectedLocation: props.selectedLocation,
      showMap: false,
    };
  }

  render() {
    const showHideMapButton = this.state.showMap ?
        (
          <Button
            className='pf-button-primary'
            type='button'
            onClick={() => this.setState({showMap: false})}>
            {this.props.intl.formatMessage(MESSAGES.hideMap)}
          </Button>
        ) :
        (
          <Button
            className='pf-button-primary'
            type='button'
            onClick={() => this.setState({showMap: true})}>
            {this.props.intl.formatMessage(MESSAGES.showMap)}
          </Button>
        );
    return (
      <div>
        <TextField
          label={this.props.intl.formatMessage(MESSAGES.lastKnownLocation)}
          outlined
          textarea
        >
          <Input
            name='last_known_location'
            value={this.state['changethis']}
            onChange={(e) => this.setState({['changethis']: e.target.value})} />
        </TextField>
        <Button
          className='pf-button-primary'
          type='button'
          onClick={() => this.populateLocationWithCurrentLocation()}>
          Use location
        </Button>
        {showHideMapButton}
        <Map display={this.state.showMap} />
      </div>
    );
  }

  populateLocationWithCurrentLocation() {
    // TODO(nworden): send this to someone who knows JS to see if this is a dumb
    // thing to do
    const outer = this;
    navigator.geolocation.getCurrentPosition(function(position) {
      outer.setState({
        selectedLocation: [position.coords.latitude, position.coords.longitude],
      });
    });
  }
}

class MapImpl extends Component {
  constructor(props) {
    super(props);
    const pinLocation = props.pinLocation || ENV.maps_default_center;
    this.state = {
      display: props.display,
      mapStartedLoading: props.display,
      // It'd be nice to store this as a google.maps.LatLng directly, but we
      // can't do that until the script is loaded.
      pinLocation: pinLocation,
    }
  }

  componentDidMount() {
    if (this.props.display) {
      this.loadMap();
    }
  }

  componentDidUpdate(prevProps, prevState) {
    if (prevProps.display != this.props.display) {
      this.setState({
        display: this.props.display,
        mapStartedLoading: prevState.mapStartedLoading || this.props.display,
      });
      if (this.props.display) {
        this.loadMap();
      }
    }
  }

  loadMap() {
    const mapNode = ReactDOM.findDOMNode(this.refs.map);
    const scriptTag = document.createElement('script');
    const pinLocation = this.state.pinLocation;
    scriptTag.src = BASE_MAPS_API_URL + '?key=' + ENV.maps_api_key;
    scriptTag.addEventListener('load', function() {
      const map = new google.maps.Map(mapNode, {
        center: {lat: ENV.maps_default_center[0],
                 lng: ENV.maps_default_center[1]},
        zoom: ENV.maps_default_zoom,
      });
      const marker = new google.maps.Marker({
        map: map,
        position: new google.maps.LatLng(pinLocation[0], pinLocation[1]),
      });
      google.maps.event.trigger(map, 'ready');
    });
    document.getElementsByTagName('body')[0].appendChild(scriptTag);
  }

  render() {
    const mapStyle = {
      display: this.state.display ? 'inherit' : 'none',
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

const Map = injectIntl(MapImpl);

export default injectIntl(LocationFieldset);
