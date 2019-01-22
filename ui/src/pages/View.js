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
import {FormattedMessage, defineMessages, injectIntl} from 'react-intl';

import LoadingIndicator from './../components/LoadingIndicator.js';

class View extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoaded: false,
      error: null,
      repo: null,
      person: null
    };
  }

  componentDidMount() {
    const personId = new URL(window.location.href).searchParams.get('id');
    // TODO(nworden): consider if we could have a global cache of repo info to
    // avoid calling for it on each page load
    var apiCalls = [
        '/' + this.props.match.params.repoId + '/d/repoinfo',
        '/' + this.props.match.params.repoId + '/d/personinfo?id=' + personId,
        ];
    Promise.all(apiCalls.map(url => fetch(url)))
        .then(res => Promise.all(res.map(r => r.json())))
        .then(
          (res) => {
            this.setState({
              isLoaded: true,
              repo: res[0],
              person: res[1]
            });
          },
          (error) => {
            this.setState({error: error});
          }
        );
  }

  render() {
    if (!this.state.isLoaded) {
      return <LoadingIndicator />;
    }
    // TODO: actually implement the page
    return (
      <div>
        {this.state.person.name}
      </div>
    );
  }
}

export default injectIntl(View);
