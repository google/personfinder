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
import {Link} from 'react-router-dom'
import Button from '@material/react-button';

import EndBarHeader from './../components/EndBarHeader.js';
import Footer from './../components/Footer.js';
import LoadingIndicator from './../components/LoadingIndicator.js';
import RepoHeader from './../components/RepoHeader.js';
import SearchBar from './../components/SearchBar.js';

const MESSAGES = defineMessages({
  howToUsePf: {
    id: 'RepoHome.howToUsePf',
    defaultMessage: 'How to use Person Finder',
    description: 'Anchor text for a link to a user guide.',
  },
  provideInfoAboutSomeone: {
    id: 'RepoHome.provideInfoAboutSomeone',
    defaultMessage: 'Provide information about someone',
    description: ('Label on a button for people who want to provide '
        + 'information about someone\'s status in the aftermath of a '
        + 'disaster.'),
  },
  or: {
    id: 'RepoHome.or',
    defaultMessage: 'Or',
    description: ('A heading for a section with one or more alternatives to '
        + 'the main option.'),
  },
  // TODO(nworden): confirm with UX that this should differ (begins with
  // "currently") from the similar message on the global homepage.
  repoRecordCount: {
    id: 'RepoHome.repoRecordCount',
    defaultMessage: 'Currently tracking {recordCount} records',
    description: ('A message displaying how many data records we have in the '
        + 'database.'),
  },
});

/*
 * A component for repo homepages.
 */
class RepoHome extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoaded: false,
      error: null,
      repo: null
    };
    this.repoId = this.props.match.params.repoId;
    this.goToCreate = this.goToCreate.bind(this);
    this.handleSearch = this.handleSearch.bind(this);
  }

  goToCreate() {
    this.props.history.push(`/${this.repoId}/create`);
  }

  handleSearch(query) {
    this.props.history.push({
        pathname: `/${this.repoId}/results`,
        search: '?query_name=' + encodeURIComponent(query),
      });
  }

  componentDidMount() {
    const apiUrl = `/${this.repoId}/d/repo`;
    fetch(apiUrl)
      .then(res => res.json())
      .then(
        (repo) => {
          this.setState({
            isLoaded: true,
            repo: repo
          });
        },
        (error) => {
          this.setState({
            isLoaded: true,
            error: error
          });
        }
      );
  }

  render() {
    if (this.state.error) {
      return <div>An error occurred</div>
    }
    if (!this.state.isLoaded) {
      return <LoadingIndicator />;
    }
    var recordCountContent = null;
    if (this.state.repo.recordCount > 0) {
      recordCountContent = (
          <p className='mdc-typography--body1 repohome-recordcount'>
            <FormattedMessage
              {...MESSAGES.repoRecordCount}
              values={{
                'recordCount': this.state.repo.recordCount
              }} />
          </p>
      );
    }
    return (
      <div>
        <RepoHeader
          repo={this.state.repo}
          backButtonTarget={'/'}
        />
        <div className='repohome-body'>
          <SearchBar
              repoId={this.repoId}
              initialValue=''
              onSearch={this.handleSearch} />
          {recordCountContent}
          <EndBarHeader>
            <FormattedMessage {...MESSAGES.or} />
          </EndBarHeader>
          <Button
            className='pf-button-secondary'
            outlined
            onClick={this.goToCreate}
          >
            {this.props.intl.formatMessage(MESSAGES.provideInfoAboutSomeone)}
          </Button>
        </div>
        <div className='org-boxwrapper repohome-footersection'>
          <p className='mdc-typography--body1 repohome-howtolink'>
            <Link to={{pathname: '/global/howto'}}>
              <FormattedMessage {...MESSAGES.howToUsePf} />
            </Link>
          </p>
          <Footer wrapped />
        </div>
      </div>);
  }
}

export default injectIntl(RepoHome);
