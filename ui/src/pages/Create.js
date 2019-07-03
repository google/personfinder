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

import Immutable from 'immutable';
import React, {Component} from 'react';
import {FormattedHTMLMessage, FormattedMessage, defineMessages, injectIntl} from 'react-intl';
import Button from '@material/react-button';
import Checkbox from '@material/react-checkbox';
import Radio, {NativeRadioControl} from '@material/react-radio';
import MenuSurface, {Corner} from '@material/react-menu-surface';
import Select from '@material/react-select';
import Tab from '@material/react-tab';
import TabBar from '@material/react-tab-bar';
import TextField, {HelperText, Input} from '@material/react-text-field';

import COMMON_MESSAGES from './../utils/CommonMessages.js';
import Footer from './../components/Footer.js';
import LoadingIndicator from './../components/LoadingIndicator.js';
import LocationFieldset from './../components/LocationFieldset.js';
import PFNotchedOutline from './../components/PFNotchedOutline.js';
import ProfilePageUtils from './../utils/ProfilePageUtils.js';
import RepoHeader from './../components/RepoHeader.js';

const MESSAGES = defineMessages({
  addSite: {
    id: 'Create.addSite',
    defaultMessage: 'Add site',
    description: ('A label on a button that lets a user add a profile page '
        + '(e.g., for Facebook or Twitter).'),
  },
  age: {
    id: 'Create.age',
    defaultMessage: 'Age',
    description: 'A label for a form field for a person\'s age.',
  },
  chooseFile: {
    id: 'Create.chooseFile',
    defaultMessage: 'Choose file',
    description: 'Label for a button for users who want to upload a photo.',
  },
  city: {
    id: 'Create.city',
    defaultMessage: 'City',
    description: 'A label for a form field for a person\'s city.',
  },
  copiedRecord: {
    id: 'Create.copiedRecord',
    defaultMessage: 'This record is copied from another source',
    description: ('An option on a form to indicate the user is copying data '
        + 'over from another source.'),
  },
  country: {
    id: 'Create.country',
    defaultMessage: 'Country',
    description: 'A label for a form field for a person\'s country.',
  },
  // This is called deleteMsg, rather than just "delete", because "delete" is a
  // keyword in JavaScript.
  deleteMsg: {
    id: 'Create.deleteMsg',
    defaultMessage: 'Delete',
    description: 'A label for a delete button.',
  },
  description: {
    id: 'Create.description',
    defaultMessage: 'Description',
    description: 'A label for a free-text field for describing a person.',
  },
  familyNameOrSurnameRequired: {
    id: 'Create.familyNameOrSurnameRequired',
    defaultMessage: 'Family name or Surname (required)',
    description: 'A label for a form field for a person\'s surname.',
  },
  givenNameOrFirstNameRequired: {
    id: 'Create.givenNameOrFirstNameRequired',
    defaultMessage: 'Given name or First name (required)',
    description: 'A label for a form field for a person\'s given name.',
  },
  identifyingInformation: {
    id: 'Create.identifyingInformation',
    defaultMessage: 'Identifying information',
    description: 'A header for a section of a form with identifying '
        + 'information (name, age, etc.).'
  },
  infoAboutMe: {
    id: 'Create.infoAboutMe',
    defaultMessage: 'Information about me',
    description: ('A label on a tab for users to submit information about '
        + 'themselves.'),
  },
  message: {
    id: 'Create.message',
    defaultMessage: 'Message',
    description: 'A message for a person, or about the person.',
  },
  moreDropdown: {
    id: 'Create.moreDropdown',
    defaultMessage: 'More&nbsp;&nbsp;&#9207;',
    description: ('A label on a button to show additional fields that are '
        + 'hidden by default.'),
  },
  newRecord: {
    id: 'Create.newRecord',
    defaultMessage: 'This is a new record',
    description: ('An option on a form to indicate that the user is creating a '
        + 'brand new record, as opposed to copying over data from another '
        + 'source.'),
  },
  noFileChosen: {
    id: 'Create.noFileChosen',
    defaultMessage: 'No file chosen...',
    description: ('Placeholder text used when a user has not (yet) chosen to '
        + 'upload a photo.'),
  },
  orEnterPhotoUrl: {
    id: 'Create.orEnterPhotoUrl',
    defaultMessage: 'Or enter photo URL',
    description: ('A label for a form field where users can submit a photo URL '
        + '(as opposed to uploading a photo directly)'),
  },
  otherPersonMessageExplanationText: {
    id: 'Create.otherPersonMessageExplanationText',
    defaultMessage: ('Write a message for this person, or for others seeking '
        + 'this person.'),
    description: ('Hint text for a form field for a message for/about a '
        + 'person. The form is used to provide or seek information about a '
        + 'person in the aftermath of a disaster, and this field is a '
        + 'free-text field that can be used to provide additional information '
        + 'about someone or to ask for information about the person.'),
  },
  photo: {
    id: 'Create.photo',
    defaultMessage: 'Photo',
    description: 'A label on a section of a form for providing a photo.',
  },
  profilePages: {
    id: 'Create.profilePages',
    defaultMessage: 'Profile pages',
    description: ('A label on a section of a form for adding profile pages '
        + '(e.g., on Facebook or Twitter).'),
  },
  provinceOrState: {
    id: 'Create.provinceOrState',
    defaultMessage: 'Province or state',
    description: 'A label for a form field for a person\'s province or state.',
  },
  selfMessageExplanationText: {
    id: 'Create.selfMessageExplanationText',
    defaultMessage: 'Write a message to the people looking for you',
    description: ('Hint text for a form field for a message the user can leave '
        + 'people looking for them in the aftermath of a disaster.'),
  },
  sex: {
    id: 'Create.sex',
    defaultMessage: 'Sex',
    description: 'A label for a sex (male/female/other) field on a form.',
  },
  sexFemale: {
    id: 'Create.sexFemale',
    defaultMessage: 'Female',
    description: 'An option on a form field for a person\'s sex.',
  },
  sexMale: {
    id: 'Create.sexMale',
    defaultMessage: 'Male',
    description: 'An option on a form field for a person\'s sex.',
  },
  sexOther: {
    id: 'Create.sexOther',
    defaultMessage: 'Other',
    description: 'An option on a form field for a person\'s sex.',
  },
  someoneElse: {
    id: 'Create.someoneElse',
    defaultMessage: 'Someone else',
    description: ('A label for a tab for users to submit information about '
        + 'someone other than themselves.'),
  },
  sourceOfRecordHeader: {
    id: 'Create.sourceOfRecordHeader',
    defaultMessage: 'Source of record',
    description: ('A header for a section of a form for information about the '
        + 'source of the rest of the form\'s information.'),
  },
  statusOfThisPersonHeader: {
    id: 'Create.statusOfThisPersonHeader',
    defaultMessage: 'Status of this person',
    description: ('A heading for a form section for information about a '
        + 'person\'s status in the aftermath of a disaster.'),
  },
  statusOfThisPersonField: {
    id: 'Create.statusOfThisPersonField',
    defaultMessage: 'Status of this person',
    description: ('A label on a field for indicating if a person is alive, '
        + 'missing, etc.'),
  },
  statusOfPersonUnspecified: {
    id: 'Create.statusOfPersonUnspecified',
    defaultMessage: 'Unspecified',
    description: 'An option to not specify the status of a person.',
  },
  statusOfPersonSeekingInfo: {
    id: 'Create.statusOfPersonSeekingInfo',
    defaultMessage: 'I am seeking information',
    description: ('An option to indicate the poster is seeking information '
        + 'about a person.')
  },
  statusOfPersonAmPerson: {
    id: 'Create.statusOfPersonAmPerson',
    defaultMessage: 'I am this person',
    description: ('An option to indicate the user is filling out the form '
        + 'about themself.'),
  },
  statusOfPersonIsAlive: {
    id: 'Create.statusOfPersonIsAlive',
    defaultMessage: 'I have received information that this person is alive',
    description: ('An option to indicate the the user has knowledge that the '
        + 'person is alive.'),
  },
  statusOfPersonIsMissing: {
    id: 'Create.statusOfPersonIsMissing',
    defaultMessage: 'I have reason to think this person is missing',
    description: ('An option to indicate that the user thinks the person is '
        + 'missing.'),
  },
  statusPersonallyTalkedTo: {
    id: 'Create.statusPersonallyTalkedTo',
    defaultMessage: ('Have you personally talked to this person AFTER the '
        + 'disaster?'),
    description: ('A label for a form field asking if the user has personally '
        + 'talked to the person they\'re filling out the form about.'),
  },
  submitRecord: {
    id: 'Create.submitRecord',
    defaultMessage: 'Submit record',
    description: 'A label on a form submission button.',
  },
  subscribeToUpdates: {
    id: 'Create.subscribeToUpdates',
    defaultMessage: 'Subscribe to updates',
    description: 'A label on a checkbox to subscribe to updates.',
  },
  yourEmail: {
    id: 'Create.yourEmail',
    defaultMessage: 'Your email',
    description: 'A label for a form field for the user\'s email address.',
  },
  yourNameRequired: {
    id: 'Create.yourNameRequired',
    defaultMessage: 'Your name (required)',
    description: ('A label for a form field for the user\'s name. It can be a '
        + 'full or a partial name.'),
  },
  yourPhoneNumber: {
    id: 'Create.yourPhoneNumber',
    defaultMessage: 'Your phone number',
    description: 'A label for a form field for the user\'s phone number.',
  },
  yourStatusHeader: {
    id: 'Create.yourStatusHeader',
    defaultMessage: 'Your status',
    description: ('A heading for a form section for information about the '
        + 'user\'s status in the aftermath of a disaster.'),
  },
});

/*
 * The Create page has two tabs: one for adding yourself and one for adding
 * another person. This enum is used to refer to the two cases.
 */
const TAB_INDICES = Object.freeze({
  ABOUT_ME: 0,
  ABOUT_SOMEONE_ELSE: 1
});

/*
 * A component for the record creation page.
 */
class Create extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoaded: false,
      error: null,
      repo: null,
      // Which of the two tabs (adding yourself or adding another person) is
      // active.
      activeTabIndex: TAB_INDICES.ABOUT_ME,
      // By default, we hide a bunch of fields in a zippy. If this is true, we
      // show them.
      showAllIdInfoFields: false,
      // When someone wants to add a profile page link, we show them a menu to
      // choose what kind of page they're adding (FB, Twitter, etc.). This
      // boolean is to track whether that menu should be visible.
      showProfilePageOptions: false,
      // This is for a reference to an element to anchor the profile page
      // options menu to; it's used by the Material MenuSurface component.
      profilePageOptionsAnchor: null,
      showMap: false,
      // By default, we hide a couple of the record source fields in a zippy. If
      // this is true, we show them.
      showAllSourceFields: false,
      // These fields are for the values of the form fields.
      formSurname: '',
      formGivenName: '',
      formSex: '',
      formAge: '',
      formDescription: '',
      formPhotoFile: null,
      formPhotoUrl: '',
      formProfilePages: Immutable.List(),
      formPersonStatus: 'unspecified',
      formLastKnownLocation: '',
    };
    this.repoId = this.props.match.params.repoId;
    this.handleSubmit = this.handleSubmit.bind(this);
    this.addProfilePageField = this.addProfilePageField.bind(this);
    this.removeProfilePageField = this.removeProfilePageField.bind(this);
    this.photoUploadInput = React.createRef();
  }

  componentDidMount() {
    const apiUrl = '/' + this.repoId + '/d/repo';
    fetch(apiUrl)
      .then(res => res.json())
      .then(
        (repo) => {
          this.setState({
            isLoaded: true,
            repo: repo,
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

  renderMoreFieldsButton() {
    return (
      <div className='create-formgroupwrapper create-morebutton'>
        <span
          className='mdc-typography--body1'
          onClick={(e) => this.setState({showAllIdInfoFields: true})}
        >
          <FormattedHTMLMessage {...MESSAGES.moreDropdown} />
        </span>
      </div>
    )
  }

  clearPhotoUpload() {
    this.photoUploadInput.current.value = '';
    this.setState({formPhotoFile: ''});
  }

  renderPhotoUploadLine() {
    // You can't really style an input element, but we don't want to display it
    // as-is, so we hide the actual input element and use a styled button as a
    // proxy. The Button below this will call click() on the input when it's
    // clicked.
    const photoInputField = (
        <input
          className='proxied-upload'
          type='file'
          ref={this.photoUploadInput}
          onChange={(e) => this.setState({formPhotoFile: e.target.files[0]})} />
    );
    if (this.state.formPhotoFile) {
      return (
          <div className='create-photouploadline'>
            {photoInputField}
            <span className='mdc-typography--body1'>
              {this.state.formPhotoFile.name}
            </span>
            <img
                className='create-photodeletebutton'
                src='/static/icons/maticon_clear.svg'
                alt={this.props.intl.formatMessage(MESSAGES.deleteMsg)}
                tabIndex='0'
                role='button'
                aria-label={this.props.intl.formatMessage(MESSAGES.deleteMsg)}
                onClick={(e) => this.clearPhotoUpload()}
                onKeyDown={(e) => {
                  return e.keyCode != 13 || this.clearPhotoUpload();
                }} />
          </div>
      );
    } else {
      return (
          <div className='create-photouploadline'>
            {photoInputField}
            <span className='mdc-typography--body1'>
              <FormattedMessage {...MESSAGES.noFileChosen} />
            </span>
            <Button
              className='pf-button-primary create-choosefilebutton'
              type='button'
              onClick={() => this.photoUploadInput.current.click()}
              disabled={this.state.formPhotoUrl != ''}>
              {this.props.intl.formatMessage(MESSAGES.chooseFile)}
            </Button>
          </div>
      );
    }
  }

  renderPhotoFields() {
    return (
      <PFNotchedOutline label={this.props.intl.formatMessage(MESSAGES.photo)}>
        {this.renderPhotoUploadLine()}
        <TextField
          label={this.props.intl.formatMessage(MESSAGES.orEnterPhotoUrl)}
          outlined
        >
          <Input
            value={this.state.formPhotoUrl}
            onChange={(e) => this.setState({formPhotoUrl: e.target.value})}
            disabled={this.state.formPhotoFile != null} />
        </TextField>
      </PFNotchedOutline>
    );
  }

  /*
   * Adds a profile page field for the given site to the form.
   */
  addProfilePageField(site) {
    this.setState({
      formProfilePages: this.state.formProfilePages.push(
          {site: site, value: ''}),
      showProfilePageOptions: false,
    });
  }

  /*
   * Removes the given profile page field from the form.
   */
  removeProfilePageField(index) {
    this.setState({
      formProfilePages: this.state.formProfilePages.delete(index),
    });
  }

  /*
   * Renders a profile field menu option for the given site.
   */
  renderProfilePageOption(site) {
    // TODO(nworden): include site icons
    return (
      <li
        className='mdc-typography--body1'
        onClick={() => this.addProfilePageField(site)}>
        <FormattedMessage {...ProfilePageUtils.SITES[site]} />
      </li>
    );
  }

  updateProfilePageValue(index, newValue) {
    let newPage = {
        site: this.state.formProfilePages.get(index).site,
        value: newValue,
    }
    this.setState({
        formProfilePages: this.state.formProfilePages.set(index, newPage),
    });
  }

  /*
   * Render the profile page link fields (if any) and the "Add site" button.
   */
  renderProfilePageFields() {
    const profilePageFields = this.state.formProfilePages.map((page, index) => (
      // Be careful with the key for this list -- for our use case, we can use
      // the index as the key, but that's not always the case.
      <div
        className='create-profilefieldwrap'
        key={index}>
        <TextField
          label={this.props.intl.formatMessage(
              ProfilePageUtils.SITES[page.site])}
          outlined
        >
          <Input
            value={page.value}
            name={'profile-url-' + index}
            onChange={(e) => this.updateProfilePageValue(index, e.target.value)}
          />
        </TextField>
        <div className='create-profilefielddelete'>
          <span onClick={() => this.removeProfilePageField(index)}>
            &times;
          </span>
        </div>
      </div>
    ));
    const profilePageOptions = (
      <MenuSurface
        open={this.state.showProfilePageOptions}
        onClose={() => this.setState({showProfilePageOptions: false})}
        anchorElement={this.state.profilePageOptionsAnchor}
        anchorCorner={Corner.BOTTOM_LEFT}>
        <ul className='create-profilepageopts'>
          {this.renderProfilePageOption('facebook')}
          {this.renderProfilePageOption('twitter')}
          {this.renderProfilePageOption('linkedin')}
          {this.renderProfilePageOption('other')}
        </ul>
      </MenuSurface>
    );
    // TODO(nworden): check with UX about how this button should be styled
    return (
      <PFNotchedOutline
        label={this.props.intl.formatMessage(MESSAGES.profilePages)}>
        {profilePageFields}
        <div
          className='mdc-menu-surface--anchor'
          ref={(el) => {
            if (!this.state.profilePageOptionsAnchor) {
              this.setState({profilePageOptionsAnchor: el});
            }
          }}>
          <Button
            className='pf-button-secondary'
            raised
            type='button'
            onClick={() => {this.setState({showProfilePageOptions: true})}}>
            {this.props.intl.formatMessage(MESSAGES.addSite)}
          </Button>
          {profilePageOptions}
        </div>
      </PFNotchedOutline>
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
          id={'forminput-' + formKey}
          value={this.state[formKey]}
          onChange={(e) => this.setState({[formKey]: e.target.value})} />
      </TextField>
    );
  }

  renderTextAreaAndInput(formKey, inputName, labelMessage) {
    return (
      <TextField
        label={this.props.intl.formatMessage(labelMessage)}
        outlined
        textarea
      >
        <Input
          name={inputName}
          id={'forminput-' + formKey}
          value={this.state[formKey]}
          onChange={(e) => this.setState({[formKey]: e.target.value})} />
      </TextField>
    );
  }

  /*
   * Renders identifying info fields that are hidden in a zippy by default.
   */
  renderMoreIdentifyingInfoFields() {
    return (
      <div className='create-formgroupwrapper'>
        <Select
          label={this.props.intl.formatMessage(MESSAGES.sex)}
          onChange={(e) => this.setState({formSex: e.target.value})}
          value={this.state.formSex}
          outlined
        >
          <option value='' />
          <option value='male'>
            {this.props.intl.formatMessage(MESSAGES.sexMale)}
          </option>
          <option value='female'>
            {this.props.intl.formatMessage(MESSAGES.sexFemale)}
          </option>
          <option value='other'>
            {this.props.intl.formatMessage(MESSAGES.sexOther)}
          </option>
        </Select>
        {this.renderTextFieldAndInput('formAge', 'age', MESSAGES.age)}
        {this.renderTextFieldAndInput('formCity', 'home_city', MESSAGES.city)}
        {this.renderTextFieldAndInput(
            'formProvinceState', 'home_state', MESSAGES.provinceOrState)}
        {this.renderTextFieldAndInput(
            'formCountry', 'home_country', MESSAGES.country)}
        {this.renderTextAreaAndInput(
            'formDescription', 'description', MESSAGES.description)}
        {this.renderPhotoFields()}
        {this.renderProfilePageFields()}
      </div>
    );
  }

  renderIdentifyingInfoFields() {
    const moreFields = this.state.showAllIdInfoFields ?
        this.renderMoreIdentifyingInfoFields() :
        this.renderMoreFieldsButton();
    return (
      <div className='create-formsectionwrapper'>
        <div className='create-formgroupwrapper'>
          <span className='mdc-typography--overline'>
            <FormattedMessage {...MESSAGES.identifyingInformation} />
          </span>
          {this.renderTextFieldAndInput(
              'formSurname', 'family_name',
              MESSAGES.familyNameOrSurnameRequired)}
          {this.renderTextFieldAndInput(
              'formGivenName', 'given_name',
              MESSAGES.givenNameOrFirstNameRequired)}
          {/*
          TODO(nworden): figure out why the checkbox doesn't line up with the
          label
          */}
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
        </div>
        {moreFields}
        {/* TODO(nworden): add status and location fields */}
      </div>
    );
  }

  renderLastKnownLocationField() {
    return (
      <div className='create-formgroupwrapper'>
        <LocationFieldset
            mapDefaultCenter={this.state.repo.mapDefaultCenter}
            mapDefaultZoom={this.state.repo.mapDefaultZoom}
            locationLatLng={this.state.locationLatLng}
            locationText={this.state.locationText}
            onLocationLatLngUpdate={
              (value) => this.setState({locationLatLng: value})}
            onLocationTextUpdate={
              (value) => this.setState({locationText: value})} />
      </div>
    );
  }

  populateLocationWithCurrentLocation() {
    const page = this;
    navigator.geolocation.getCurrentPosition(function(position) {
      const positionStr =
          position.coords.latitude + ', ' + position.coords.longitude;
      page.setState({formLastKnownLocation: positionStr});
    });
  }

  renderStatusFields() {
    const headerMessage = this.state.activeTabIndex == TAB_INDICES.ABOUT_ME ?
        MESSAGES.yourStatusHeader :
        MESSAGES.statusOfThisPersonHeader;
    const statusField = this.state.activeTabIndex == TAB_INDICES.ABOUT_ME ?
        <input type='hidden' name='status' value='is_note_author' /> :
        (
            <Select
                label={this.props.intl.formatMessage(
                    MESSAGES.statusOfThisPersonField)}
                name='status'
                id='forminput-formPersonStatus'
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
        );
    const messageExplanationTextMessage = (
        this.state.activeTabIndex == TAB_INDICES.ABOUT_ME ?
        MESSAGES.selfMessageExplanationText :
        MESSAGES.otherPersonMessageExplanationText);
    const talkedToField = this.state.activeTabIndex == TAB_INDICES.ABOUT_ME ?
        null :
        (
            <div>
              <p className='mdc-typography--body1'>
                <FormattedMessage {...MESSAGES.statusPersonallyTalkedTo} />
              </p>
              <div>
                <Radio
                  label={this.props.intl.formatMessage(COMMON_MESSAGES.yes)}
                  key='yes'
                >
                  <NativeRadioControl
                    name='author_made_contact'
                    id='forminput-authormadecontact-yes'
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
                    id='forminput-authormadecontact-no'
                    value='no'
                    onChange={(e) => this.setState(
                        {statusMadeContact: e.target.value})} />
                </Radio>
              </div>
            </div>
        );
    return (
      <div className='create-formsectionwrapper'>
        <div className='create-formgroupwrapper'>
          <span className='mdc-typography--overline'>
            <FormattedMessage {...headerMessage} />
          </span>
          {statusField}
          {this.renderTextAreaAndInput(
              'formStatusMessage', 'message', MESSAGES.message)}
          <p className='mdc-typography--body1 form-explanationtext'>
            <FormattedMessage {...messageExplanationTextMessage} />
          </p>
          {talkedToField}
        </div>
        { this.renderLastKnownLocationField() }
      </div>
    );
  }

  renderSourceFields() {
    if (this.state.activeTabIndex == TAB_INDICES.ABOUT_ME) {
      return null;
    }
    const moreSection = this.state.showAllSourceFields ?
        (
            <div className='create-formgroupwrapper'>
              {this.renderTextFieldAndInput(
                  'formAuthorEmail', 'author_email', MESSAGES.yourEmail)}
              {this.renderTextFieldAndInput(
                  'formAuthorPhone', 'author_phone', MESSAGES.yourPhoneNumber)}
            </div>
        ) :
        (
            <div className='create-formgroupwrapper create-morebutton'>
              <span
                className='mdc-typography--body1'
                onClick={(e) => this.setState({showAllSourceFields: true})}
              >
                <FormattedHTMLMessage {...MESSAGES.moreDropdown} />
              </span>
            </div>
        );
    return (
        <div className='create-formsectionwrapper create-sourcesection'>
          <div className='create-formgroupwrapper'>
            <span className='mdc-typography--overline'>
              <FormattedMessage {...MESSAGES.sourceOfRecordHeader} />
            </span>
            <div>
              <Radio
                label={this.props.intl.formatMessage(MESSAGES.newRecord)}
                key='yes'
              >
                <NativeRadioControl
                  name='clone'
                  id='forminput-clone-yes'
                  value='yes'
                  onChange={(e) => this.setState(
                      {formClone: e.target.value})} />
              </Radio>
            </div>
            <div>
              <Radio
                label={this.props.intl.formatMessage(MESSAGES.copiedRecord)}
                key='no'
              >
                <NativeRadioControl
                  name='clone'
                  id='forminput-clone-no'
                  value='no'
                  onChange={(e) => this.setState(
                      {formClone: e.target.value})} />
              </Radio>
            </div>
            {this.renderTextFieldAndInput(
                'formAuthorName', 'author_name', MESSAGES.yourNameRequired)}
          </div>
          {moreSection}
        </div>
    );
  }

  handleSubmit(e) {
    // TODO(nworden): show the loading indicator as soon as the search starts
    e.preventDefault();
    const apiUrl = '/' + this.repoId + '/d/create';
    const formData = new FormData(e.target);
    formData.set('photo', this.state.formPhotoFile);
    fetch(apiUrl, {method: 'POST', body: formData})
      .then(res => res.json())
      .then(
        (res) => {
          this.props.history.push({
            pathname: '/' + this.repoId + '/view',
            search: '?id=' + res.personId,
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
    if (this.state.error) {
      // TODO(nworden): add a useful and i18n'd error message
      return <div>An error occurred</div>
    }
    if (!this.state.isLoaded) {
      return <LoadingIndicator />;
    }
    const formContent = (
      <div className='create-formwrapper'>
        <input
            type='hidden'
            name='own_info'
            value={this.state.activeTabIndex == TAB_INDICES.ABOUT_ME ?
                'yes' : 'no'} />
        {this.renderIdentifyingInfoFields()}
        {this.renderStatusFields()}
        {this.renderSourceFields()}
      </div>
    );
    return (
      <div className='pf-linearwrap'>
        {/* TODO(nworden): consider having this go back to search results when
            applicable */}
        <RepoHeader
          repo={this.state.repo}
          backButtonTarget={'/' + this.repoId}
        />
        <div className='create-tabwrapper'>
          <TabBar
            activeIndex={this.state.activeTabIndex}
            handleActiveIndexUpdate={
                (index) => {this.setState({activeTabIndex: index})}
            }
          >
            <Tab>
              <span className='mdc-tab__text-label'>
                <FormattedMessage {...MESSAGES.infoAboutMe} />
              </span>
            </Tab>
            <Tab>
              <span className='mdc-tab__text-label'>
                <FormattedMessage {...MESSAGES.someoneElse} />
              </span>
            </Tab>
          </TabBar>
        </div>
        <form onSubmit={this.handleSubmit}>
          <input
            type='hidden'
            name='add_type'
            value={this.state.activeTabIndex}
          />
          {formContent}
          <Button
            className='pf-button-primary create-submitbutton'
            type='submit'>
            {this.props.intl.formatMessage(MESSAGES.submitRecord)}
          </Button>
        </form>
        <Footer />
      </div>
    );
  }
}

export default injectIntl(Create);
