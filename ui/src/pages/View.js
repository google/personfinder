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
import Fab from '@material/react-fab';

import Footer from './../components/Footer.js';
import LoadingIndicator from './../components/LoadingIndicator.js';
import Note from './../components/Note.js';
import ProfilePageUtils from './../utils/ProfilePageUtils.js';
import RepoHeader from './../components/RepoHeader.js';
import SearchBar from './../components/SearchBar.js';
import Utils from './../utils/Utils.js';

// TODO(gimite): Consider sharing some messages with Create.js because they
// have many overlaps.
const MESSAGES = defineMessages({
  addNote: {
    id: 'View.addNote',
    defaultMessage: 'Add note',
    description: ('A label on a button that takes the user to a page where '
        + 'they can add a note with an update on a person\'s status or a '
        + 'message for the person.'),
  },
  age: {
    id: 'View.age',
    defaultMessage: 'Age',
    description: 'A label for a person\'s age.',
  },
  authorOfThisRecord: {
    id: 'View.authorOfThisRecord',
    defaultMessage: 'Author of this record',
    description: ('The title of a section with information about the source / '
        + 'author of the rest of the information on the page.'),
  },
  city: {
    id: 'View.city',
    defaultMessage: 'City',
    description: 'A label for a person\'s city.',
  },
  clickToReveal: {
    id: 'View.clickToReveal',
    defaultMessage: 'Click to reveal',
    description: 'A label for a button to show sensitive information which is hidden by default e.g., phone number.',
  },
  country: {
    id: 'View.country',
    defaultMessage: 'Country',
    description: 'A label for a person\'s country.',
  },
  description: {
    id: 'View.description',
    defaultMessage: 'Description',
    description: ('The title of a section with free text description to '
        + 'identify a specific person.'),
  },
  email: {
    id: 'View.email',
    defaultMessage: 'Email',
    description: 'A label for a person\'s email address.',
  },
  homeAddress: {
    id: 'View.homeAddress',
    defaultMessage: 'Home address',
    description: 'A label for a person\'s home address.',
  },
  identifyingInformation: {
    id: 'View.identifyingInformation',
    defaultMessage: 'Identifying information',
    description: 'The title of a section which contains a person\'s '
        + 'identifying information (name, age, etc.).'
  },
  name: {
    id: 'View.name',
    defaultMessage: 'Name',
    description: 'A label for a person\'s name.',
  },
  notesForThisPerson: {
    id: 'View.notesForThisPerson',
    defaultMessage: 'Notes for this person',
    description: ('The title of a section which contains notes with updates '
        + 'or additional information about the status of the person described '
        + 'on the page.'),
  },
  originalPostingDate: {
    id: 'View.originalPostingDate',
    defaultMessage: 'Original posting date',
    description: ('A label for a date when the information on this page was '
        + 'originally posted.'),
  },
  originalSiteName: {
    id: 'View.originalSiteName',
    defaultMessage: 'Original site name',
    description: ('A label for the name of a site where the information on '
        + 'this page was originally posted.'),
  },
  phoneNumber: {
    id: 'View.phoneNumber',
    defaultMessage: 'Phone number',
    description: 'A label for a person\'s phone number.',
  },
  profilePages: {
    id: 'View.profilePages',
    defaultMessage: 'Profile pages',
    description: ('The title of a section which contains a person\'s profile '
        + 'pages (e.g., on Facebook or Twitter).'),
  },
  provinceOrState: {
    id: 'View.provinceOrState',
    defaultMessage: 'Province or state',
    description: 'A label for a person\'s province or state.',
  },
  sex: {
    id: 'View.sex',
    defaultMessage: 'Sex',
    description: 'A label for a person\'s sex (male/female/other).',
  },
  sexFemale: {
    id: 'View.sexFemale',
    defaultMessage: 'Female',
    description: 'A value for a person\'s sex.',
  },
  sexMale: {
    id: 'View.sexMale',
    defaultMessage: 'Male',
    description: 'A value for a person\'s sex.',
  },
  sexOther: {
    id: 'View.sexOther',
    defaultMessage: 'Other',
    description: 'A value for a person\'s sex.',
  },
  streetName: {
    id: 'View.streetName',
    defaultMessage: 'Street name',
    description: 'A label for a person\'s street address.',
  },
});

const SEX_VALUE_MESSAGES = {
  female: MESSAGES.sexFemale,
  male: MESSAGES.sexMale,
  other: MESSAGES.sexOther,
}

/**
 * A page which shows a specific person record.
 */
class View extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoaded: false,
      error: null,
      repo: null,
      person: null
    };
    this.handleSearch = this.handleSearch.bind(this);
    this.goToAddNote = this.goToAddNote.bind(this);
  }

  componentDidMount() {
    this.personId = Utils.getURLParam(this.props, 'id');
    this.repoId = this.props.match.params.repoId;
    // TODO(nworden): consider if we could have a global cache of repo info to
    // avoid calling for it on each page load
    const apiURLs = [
        `/${this.repoId}/d/repo`,
        `/${this.repoId}/d/person?id=${encodeURIComponent(this.personId)}`,
        ];
    Promise.all(apiURLs.map(url => fetch(url)))
        .then(res => Promise.all(res.map(r => r.json())))
        .then(
          ([repo, person]) => {
            this.setState({
              isLoaded: true,
              repo: repo,
              person: person,
            });
          },
          (error) => {
            this.setState({error: error});
          }
        );
  }

  handleSearch(query) {
    this.setState({isLoaded: false});
    this.props.history.push({
        pathname: `/${this.repoId}/results`,
        search: '?query_name=' + encodeURIComponent(query),
      });
  }

  goToAddNote() {
    this.props.history.push({
          pathname: `/${this.repoId}/add_note`,
          search: '?id=' + encodeURIComponent(this.personId),
      });
  }

  renderField(labelMessage, value, key) {
    if (value == null || value === '') {
      return null;
    }
    return (
      <div key={key}>
        <span className='view-fieldname'>
          <FormattedMessage {...labelMessage} />:
        </span>
        <span> </span>
        <span className='view-fieldvalue'>
          {value}
        </span>
      </div>
    );
  }

  getSexValue() {
    if (this.state.person.sex == null) {
      return null;
    } else {
      return this.props.intl.formatMessage(
          SEX_VALUE_MESSAGES[this.state.person.sex]);
    }
  }

  renderProfilePages() {
    return this.state.person.profile_pages.map((page, index) => {
      // TODO(gimite): Change the link text from URL to profile name
      // e.g., '@google' for Twitter.
      return this.renderField(
          ProfilePageUtils.SITES[page.site],
          <a target='_blank' href={page.value}>{page.value}</a>,
          index);
    });
  }

  renderPerson() {
    return (
      <div className='view-card'>
        {/* TODO(gimite): Add drop down menu. */}
        <div className='view-section'>
          <div className='view-headline'>
            <div className='view-headlinephoto'>
              <img src={this.state.person.localPhotoUrl} />
            </div>
            <div className='view-headlinecontent'>
              <h5 className='mdc-typography--headline5'>
                {this.state.person.name}
              </h5>
              <p className='mdc-typography--body1'>
                {/* TODO(gimite): implement this for real */}
                Record created on March 31
              </p>
            </div>
          </div>
        </div>

        <div className='view-section'>
          <div className='view-topic'>
            <h2 className='mdc-typography--subtitle2'>
              <FormattedMessage {...MESSAGES.identifyingInformation} />
            </h2>
            <div className='mdc-typography--body1'>
              {this.renderField(MESSAGES.sex, this.getSexValue())}
              {this.renderField(MESSAGES.age, this.state.person.age)}
            </div>
          </div>

          <div className='view-topic'>
            <h2 className='mdc-typography--subtitle2'>
              <FormattedMessage {...MESSAGES.homeAddress} />
            </h2>
            <div className='mdc-typography--body1'>
              {this.renderField(
                   MESSAGES.streetName, this.state.person.home_street)}
              {this.renderField(
                   MESSAGES.city, this.state.person.home_city)}
              {this.renderField(
                   MESSAGES.provinceOrState, this.state.person.home_state)}
              {this.renderField(
                   MESSAGES.country, this.state.person.home_country)}
            </div>
          </div>

          <div className='view-topic'>
            <h2 className='mdc-typography--subtitle2'>
              <FormattedMessage {...MESSAGES.description} />
            </h2>
            <div className='mdc-typography--body1'>
              <div className='view-fieldvalue'>{this.state.person.description}</div>
            </div>
          </div>

          {this.state.person.profile_pages.length > 0 ?
              <div className='view-topic'>
                <h2 className='mdc-typography--subtitle2'>
                  <FormattedMessage {...MESSAGES.profilePages} />
                </h2>
                <div className='mdc-typography--body1'>
                  {this.renderProfilePages()}
                </div>
              </div>
              : null
          }
        </div>

        <div className='view-section'>
          <div className='view-topic'>
            <h2 className='mdc-typography--subtitle2'>
              <FormattedMessage {...MESSAGES.authorOfThisRecord} />
            </h2>
            <div className='mdc-typography--body1'>
              {this.renderField(MESSAGES.name, this.state.person.author_name)}
              {/* TODO(gimite): Implement these. */}
              {this.renderField(MESSAGES.phoneNumber,
                   <a href='#'><FormattedMessage {...MESSAGES.clickToReveal} /></a>)}
              {this.renderField(MESSAGES.email,
                   <a href='#'><FormattedMessage {...MESSAGES.clickToReveal} /></a>)}
              {this.renderField(MESSAGES.originalPostingDate, this.state.person.source_date)}
              {this.renderField(MESSAGES.originalSiteName, this.state.person.source_name)}
            </div>
          </div>
        </div>
      </div>
    );
  }

  renderNotes() {
    const noteElements = this.state.person.notes.map(note => {
      return (<Note note={note} key={note.note_record_id} />);
    });

    return (
      <div>
        <h5 className='mdc-typography--headline5'>
          <FormattedMessage {...MESSAGES.notesForThisPerson} />
        </h5>
        {/* TODO(gimite): Add feed icon. */}
        {noteElements}
      </div>
    );
  }

  renderAddNoteFab() {
    return (
      <Fab
          className='results-addfab'
          onClick={this.goToAddNote}
          icon={<img src='/static/icons/maticon_add.svg' />}
          textLabel={this.props.intl.formatMessage(MESSAGES.addNote)}
      />
    );
  }

  render() {
    if (!this.state.isLoaded) {
      return <LoadingIndicator />;
    }
    return (
      <div id='view-wrapper'>
        <RepoHeader
          repo={this.state.repo}
          backButtonTarget={`/${this.repoId}`}
        />
        <div className='view-body'>
          <SearchBar
            repoId={this.repoId}
            initialValue={Utils.getURLParam(this.props, 'query_name')}
            onSearch={this.handleSearch}
          />
          {this.renderPerson()}
          {this.renderNotes()}
          <Footer />
        </div>
        {this.renderAddNoteFab()}
      </div>
    );
  }
}

export default injectIntl(View);
