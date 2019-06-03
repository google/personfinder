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
import {defineMessages, injectIntl} from 'react-intl';
import {withRouter} from 'react-router-dom';
import Button from '@material/react-button';
import TextField, {HelperText, Input} from '@material/react-text-field';

const MESSAGES = defineMessages({
  searchForAPerson: {
    id: 'SearchBar.searchForAPerson',
    defaultMessage: 'Search for a person',
    description: 'Label on a form for searching for information about someone.',
  },
});

class LocationFieldset extends Component {
  constructor(props) {
    super(props);
    this.state = {
      showMap: false,
    };
  }

  render() {
    return (
      <div>
        <Button
          className='pf-button-primary'
          type='button'
          onClick={() => this.setState({showMap: true})}>
          Show map
        </Button>
        <Map display={this.state.showMap} />
      </div>
    );
  }
}

class MapImpl extends Component {
  constructor(props) {
    super(props);
    this.state = {
      display: props.display,
      mapIsLoaded: false,
    }
    //this.handleKeyDown = this.handleKeyDown.bind(this);
  }

  handleKeyDown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      this.props.onSearch(this.state.value);
    }
  }

  toggleMapDisplay(display) {
    const needToLoadMap = display && !this.state.mapIsLoaded;
    this.setState({display: true});
    if (needToLoadMap) {
      this.loadMap();
    }
  }

  loadMap() {
    this.setState({mapIsLoaded: true});
  }

  render() {
    const mapStyle = {display: this.state.display ? 'inherit' : 'none'};
    return (
      <div ref='map' style={mapStyle}>
        Map is loading
      </div>
    );
  }
}

const Map = injectIntl(MapImpl);

export default injectIntl(LocationFieldset);
