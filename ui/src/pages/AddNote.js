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
import Button from '@material/react-button';
import Checkbox from '@material/react-checkbox';
import Radio, {NativeRadioControl} from '@material/react-radio';
import Select from '@material/react-select';
import TextField, {HelperText, Input} from '@material/react-text-field';

import COMMON_MESSAGES from './../utils/CommonMessages.js';
import Footer from './../components/Footer.js';
import LoadingIndicator from './../components/LoadingIndicator.js';
import RepoHeader from './../components/RepoHeader.js';
import Utils from './../utils/Utils.js';

const MESSAGES = defineMessages({
  messageRequired: {
    id: 'AddNote.messageRequired',
    defaultMessage: 'Message (required)',
    description: ('A label on a form field for a message to and/or about a '
        + 'person. The message might get displayed to other people looking for '
        + 'information about the person.'),
  },
  sourceOfThisNote: {
    id: 'AddNote.sourceOfThisNote',
    defaultMessage: 'Source of this note',
    description: ('A heading for a section of a form for information (name, '
          + 'email, etc.) about the person filling out the form.'),
  },
  statusOfThisPersonField: {
    id: 'AddNote.statusOfThisPersonField',
    defaultMessage: 'Status of this person',
    description: ('A label on a field for indicating if a person is alive, '
        + 'missing, etc.'),
  },
  statusOfThisPersonHeader: {
    id: 'AddNote.statusOfThisPersonHeader',
    defaultMessage: 'Status of this person',
    description: ('A heading for a form section for information about a '
        + 'person\'s status.'),
  },
  statusOfPersonUnspecified: {
    id: 'AddNote.statusOfPersonUnspecified',
    defaultMessage: 'Unspecified',
    description: 'An option to not specify the status of a person.',
  },
  statusOfPersonSeekingInfo: {
    id: 'AddNote.statusOfPersonSeekingInfo',
    defaultMessage: 'I am seeking information',
    description: ('An option to indicate the poster is seeking information '
        + 'about a person.')
  },
  statusOfPersonAmPerson: {
    id: 'AddNote.statusOfPersonAmPerson',
    defaultMessage: 'I am this person',
    description: ('An option to indicate the user is filling out the form '
        + 'about themself.'),
  },
  statusOfPersonIsAlive: {
    id: 'AddNote.statusOfPersonIsAlive',
    defaultMessage: 'I have received information that this person is alive',
    description: ('An option to indicate the the user has knowledge that the '
        + 'person is alive.'),
  },
  statusOfPersonIsMissing: {
    id: 'AddNote.statusOfPersonIsMissing',
    defaultMessage: 'I have reason to think this person is missing',
    description: ('An option to indicate that the user thinks the person is '
        + 'missing.'),
  },
  statusPersonallyTalkedTo: {
    id: 'AddNote.statusPersonallyTalkedTo',
    defaultMessage: ('Have you personally talked to this person AFTER the '
        + 'disaster?'),
    description: ('A label for a form field asking if the user has personally '
        + 'talked to the person they\'re filling out the form about.'),
  },
  submitNote: {
    id: 'AddNote.submitNote',
    defaultMessage: 'Submit note',
    description: 'A label on a form submission button.',
  },
  subscribeToUpdates: {
    id: 'AddNote.subscribeToUpdates',
    defaultMessage: 'Subscribe to updates about this person',
    description: 'A label on a checkbox to subscribe to updates.',
  },
  yourEmailRequired: {
    id: 'AddNote.yourEmailRequired',
    defaultMessage: 'Your email (required)',
    description: 'A label on a form field for the user\'s email address.',
  },
  yourNameRequired: {
    id: 'AddNote.yourNameRequired',
    defaultMessage: 'Your name (required)',
    description: 'A label on a form field for the user\'s name.',
  },
  yourPhoneNumber: {
    id: 'AddNote.yourPhoneNumber',
    defaultMessage: 'Your phone number',
    description: 'A label on a form field for the user\'s phone number.',
  },
});

/**
 * A page for adding a note.
 */
class AddNote extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoaded: false,
      error: null,
      repo: null,
      person: null,
      formAuthorEmail: '',
      formAuthorName: '',
      formAuthorPhone: '',
      formPersonStatus: 'unspecified',
    };
    this.handleSubmit = this.handleSubmit.bind(this);
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

  renderTextFieldAndInput(formKey, inputName, labelMessage) {
    return (
        <TextField
          label={this.props.intl.formatMessage(labelMessage)}
          outlined
        >
          <Input
            name={inputName}
            value={this.state[formKey]}
            onChange={(e) => this.setState({[formKey]: e.target.value})} />
        </TextField>
    );
  }

  renderForm() {
    return (
      <div>
        <div className='addnote-formsectionwrapper'>
          <div className='addnote-formgroupwrapper'>
            <span className='mdc-typography--overline'>
              <FormattedMessage {...MESSAGES.statusOfThisPersonHeader} />
            </span>
            <Select
                label={this.props.intl.formatMessage(
                    MESSAGES.statusOfThisPersonField)}
                onChange={(e) => this.setState(
                    {formPersonStatus: e.target.value})}
                value={this.state.formPersonStatus}
                outlined
            >
              <option value='unspecified'>
                {this.props.intl.formatMessage(
                    MESSAGES.statusOfPersonUnspecified)}
              </option>
              <option value='information_sought'>
                {this.props.intl.formatMessage(
                    MESSAGES.statusOfPersonSeekingInfo)}
              </option>
              <option value='is_note_author'>
                {this.props.intl.formatMessage(MESSAGES.statusOfPersonAmPerson)}
              </option>
              <option value='believed_alive'>
                {this.props.intl.formatMessage(MESSAGES.statusOfPersonIsAlive)}
              </option>
              <option value='believed_missing'>
                {this.props.intl.formatMessage(MESSAGES.statusOfPersonIsMissing)}
              </option>
            </Select>
            <TextField
              label={this.props.intl.formatMessage(MESSAGES.messageRequired)}
              outlined
              textarea
            >
              <Input
                name='text'
                value={this.state['formMessage']}
                onChange={(e) => this.setState({['formMessage']: e.target.value})} />
            </TextField>
            <p>
              <FormattedMessage {...MESSAGES.statusPersonallyTalkedTo} />
            </p>
            <div>
              <Radio
                label={this.props.intl.formatMessage(COMMON_MESSAGES.yes)}
                key='yes'
              >
                <NativeRadioControl
                  name='author_made_contact'
                  value='yes'
                  onChange={(e) => this.setState(
                      {statusMadeContact: e.target.value})} />
              </Radio>
            </div>
            <div>
              <Radio
                label={this.props.intl.formatMessage(COMMON_MESSAGES.no)}
                key='no'
              >
                <NativeRadioControl
                  name='author_made_contact'
                  value='no'
                  onChange={(e) => this.setState(
                      {statusMadeContact: e.target.value})} />
              </Radio>
            </div>
          </div>
        </div>
        <div className='addnote-formsectionwrapper'>
          <div className='addnote-formgroupwrapper'>
            <span className='mdc-typography--overline'>
              <FormattedMessage {...MESSAGES.sourceOfThisNote} />
            </span>
            {this.renderTextFieldAndInput(
                'formAuthorName', 'author_name', MESSAGES.yourNameRequired)}
            <Checkbox
              name='subscribe'
              nativeControlId='subscribetoupdates-checkbox'
              checked={this.state.formSubscribeToUpdates}
              onChange={(e) => this.setState({
                formSubscribeToUpdates: e.target.checked
              })}
            />
            <label
              className='mdc-typography--body1'
              htmlFor='subscribetoupdates-checkbox'>
              <FormattedMessage {...MESSAGES.subscribeToUpdates} />
            </label>
            {this.renderTextFieldAndInput(
                'formAuthorEmail', 'author_email', MESSAGES.yourEmailRequired)}
            {this.renderTextFieldAndInput(
                'formAuthorPhone', 'author_phone', MESSAGES.yourPhoneNumber)}
          </div>
        </div>
      </div>
    );
  }

  handleSubmit(e) {
    // TODO(nworden): show the loading indicator as soon as the search starts
    e.preventDefault();
    const apiUrl = '/' + this.repoId + '/d/add_note';
    const formData = new FormData(e.target);
    fetch(apiUrl, {method: 'POST', body: formData})
      .then(res => res.json())
      .then(
        (res) => {
          this.props.history.push({
            pathname: '/' + this.repoId + '/view',
            search: '?id=' + this.personId,
          });
        },
        (error) => {
          this.setState({
            error: error
          });
        }
      );
  }

  render() {
    if (!this.state.isLoaded) {
      return <LoadingIndicator />;
    }
    return (
      <div id='addnote-wrapper'>
        <RepoHeader
          repo={this.state.repo}
          backButtonTarget={`/${this.repoId}`}
        />
        <div className='addnote-body'>
          <form onSubmit={this.handleSubmit}>
            <input
              type='hidden'
              name='id'
              value={this.personId}
            />
            {this.renderForm()}
            <Button
                className='pf-button-primary addnote-submitbutton'
                type='submit'>
                {this.props.intl.formatMessage(MESSAGES.submitNote)}
          </Button>
          </form>
          <Footer />
        </div>
      </div>
    );
  }
}

export default injectIntl(AddNote);
