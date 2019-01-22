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
import {withRouter} from 'react-router-dom';
import Fab from '@material/react-fab';

import Footer from './../components/Footer.js';
import LoadingIndicator from './../components/LoadingIndicator.js';
import RepoHeader from './../components/RepoHeader.js';
import SearchBar from './../components/SearchBar.js';

const messages = defineMessages({
  createNewRecord: {
    id: 'Results.createNewRecord',
    defaultMessage: 'Create new record',
    description: 'Label on a button for creating a new database entry.',
  },
  noResultsFound: {
    id: 'Results.noResultsFound',
    defaultMessage: 'No results found.',
    description: 'A message shown when a search query has produced no results.',
  },
});

/*
 * A component for showing a search results page.
 */
class Results extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoaded: false,
      error: null,
      repo: null,
      results: null
    };
    this.goToAdd = this.goToAdd.bind(this);
    this.loadResults = this.loadResults.bind(this);
    this.handleSearch = this.handleSearch.bind(this);
  }

  goToAdd() {
    this.props.history.push({
          pathname: '/' + this.props.match.params.repoId + '/create',
      });
  }

  loadResults() {
    const query = new URL(window.location.href).searchParams.get('query_name');
    var apiCalls = [
        '/' + this.props.match.params.repoId + '/d/repoinfo',
        '/' + this.props.match.params.repoId + '/d/results?query=' + query,
        ];
    Promise.all(apiCalls.map(url => fetch(url)))
        .then(res => Promise.all(res.map(r => r.json())))
        .then(
          (res) => {
            this.setState({
              isLoaded: true,
              repo: res[0],
              results: res[1]
            });
          },
          (error) => {
            this.setState({error: error});
          }
        );
  }

  componentDidMount() {
    this.loadResults();
  }

  handleSearch(query) {
    this.setState({isLoaded: false});
    this.props.history.push({
        pathname: '/' + this.props.match.params.repoId + '/results',
        search: '?query_name=' + query,
      });
    this.loadResults();
  }

  renderResults() {
    if (this.state.results.length == 0) {
      return (
        <p className='mdc-typography--body1'>
          <FormattedMessage {...messages.noResultsFound} />
        </p>
      );
    }
    var results = this.state.results.map(result => (
      <SearchResult
        key={result.personId}
        repo={this.state.repo}
        result={result}
      />
    ));
    return <ul className='results-list'>{results}</ul>;
  }

  renderAddPersonFab() {
    return (
      <Fab
          className='results-addpersonfab'
          onClick={this.goToAdd}
          icon={<img src='/static/icons/maticon_add.svg' />}
          textLabel={this.props.intl.formatMessage(
              messages.createNewRecord)} />
    );
  }

  render() {
    if (this.state.error) {
      return <div>An error occurred</div>
    }
    if (!this.state.isLoaded) {
      return <LoadingIndicator />;
    }
    return (
      <div id='results-wrapper'>
        <RepoHeader
          repo={this.state.repo}
          backButtonTarget={'/' + this.state.repo.repoId}
        />
        <div className='results-body'>
          <SearchBar
              repoId={this.props.match.params.repoId}
              initialValue={
                  new URL(window.location.href).searchParams.get('query_name')}
              onSearch={this.handleSearch} />
          {this.renderResults()}
          <Footer />
        </div>
        {this.renderAddPersonFab()}
      </div>);
  }
}

/**
 * A component for an individual search result.
 */
class SearchResultImpl extends Component {
  constructor(props) {
    super(props);
    this.goTo = this.goTo.bind(this);
  }

  goTo() {
    this.props.history.push(
        '/' + this.props.repo.repoId + '/view?id='
        + this.props.result.personId);
  }

  render() {
    return (
      <li className='results-result' onClick={this.goTo}>
        <div className='results-resultphoto'>
          <img src={this.props.result.photoUrl} />
        </div>
        <div className='results-resultcontent'>
          <h5 className='mdc-typography--headline5'>
            {this.props.result.name}
          </h5>
          <p className='mdc-typography--body1'>
            {/* TODO(nworden): implement this for real */}
            Record created on March 31
          </p>
        </div>
      </li>
    );
  }
}

const SearchResult = withRouter(injectIntl(SearchResultImpl));

export default injectIntl(Results);
