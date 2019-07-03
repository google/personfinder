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
import TextField, {HelperText, Input} from '@material/react-text-field';

const MESSAGES = defineMessages({
  searchForAPerson: {
    id: 'SearchBar.searchForAPerson',
    defaultMessage: 'Search for a person',
    description: 'Label on a form for searching for information about someone.',
  },
});

class SearchBar extends Component {
  constructor(props) {
    super(props);
    this.state = {
      value: (props.initialValue == null ? '' : props.initialValue)};
    this.handleKeyDown = this.handleKeyDown.bind(this);
  }

  componentDidUpdate(prevProps) {
    if (prevProps.initialValue != this.props.initialValue) {
      this.setState({value: this.props.initialValue});
    }
  }

  handleKeyDown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      this.props.onSearch(this.state.value);
    }
  }

  render() {
    return (
        <div className='searchbar-wrapper'>
          <TextField
            label={this.props.intl.formatMessage(MESSAGES.searchForAPerson)}
            outlined
            className='searchbar'
          >
            <Input
              value={this.state.value}
              onKeyDown={this.handleKeyDown}
              onChange={(e) => this.setState({value: e.target.value})} />
          </TextField>
        </div>
    );
  }
}

export default injectIntl(SearchBar);
