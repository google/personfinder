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

import Card from '@material/react-card';
import React, {Component} from 'react';
import {FormattedMessage, defineMessages, injectIntl} from 'react-intl';

const MESSAGES = defineMessages({
  unspecified: {
    id: 'Note.unspecified',
    defaultMessage: 'Unspecified',
    description: ('An option for "Status" field of a note about a specific '
        + 'person, indicating that the status of the person is unspecified.'),
  },
  informationSought: {
    id: 'Note.informationSought',
    defaultMessage: 'I am seeking information',
    description: ('An option for "Status" field of a note about a specific '
        + 'person, indicating that the author of the note is seeking '
        + 'information on the person in question.'),
  },
  isNoteAuthor: {
    id: 'Note.isNoteAuthor',
    defaultMessage: 'I am this person',
    description: ('An option for "Status" field of a note about a specific '
        + 'person, indicating that the author of the note is the person in '
        + 'question.'),
  },
  believedAlive: {
    id: 'Note.believedAlive',
    defaultMessage: 'I have received information that this person is alive',
    description: ('An option for "Status" field of a note about a specific '
        + 'person, indicating that the author of the note has received '
        + 'information that the person in question is alive.'),
  },
  believedMissing: {
    id: 'Note.believedMissing',
    defaultMessage: 'I have reason to think this person is missing',
    description: ('An option for "Status" field of a note about a specific '
        + 'person, indicating that the author of the note has reason to '
        + 'believe that the person in question is still missing.'),
  },
  believedDead: {
    id: 'Note.believedDead',
    defaultMessage: 'I have received information that this person is dead',
    description: ('An option for "Status" field of a note about a specific '
        + 'person, indicating that author of the note has received '
        + 'information that the person in question is dead.'),
  },
  authorMadeContact: {
    id: 'Note.authorMadeContact',
    defaultMessage: 'This person has been in contact with someone',
    description: ('A message which can be attached to a note about a specific '
        + 'person.'),
  },
  lastKnownLocation: {
    id: 'Note.lastKnownLocation',
    defaultMessage: 'Last known location',
    description: ('A label for a field of a note about a specific person, '
        + 'containing the last known location of the person.'),
  },
  map: {
    id: 'Note.map',
    defaultMessage: 'Map',
    description: ('A label for a button which shows a map.'),
  },
  postedBy: {
    id: 'Note.postedBy',
    defaultMessage: 'Posted by {authorName}',
    description: ('A title of a note about a speicifc person, indicating the '
        + 'name of the author of the note.'),
  },
  status: {
    id: 'Note.status',
    defaultMessage: 'Status',
    description: ('A label of a field in a note about a speicifc person, '
        + 'indicating the status of the person sought or found e.g., the '
        + 'person is alive, missing or dead.'),
  },
});

const STATUS_MESSAGES = {
  '': MESSAGES.unspecified,
  'information_sought': MESSAGES.informationSought,
  'is_note_author': MESSAGES.isNoteAuthor,
  'believed_alive': MESSAGES.believedAlive,
  'believed_missing': MESSAGES.believedMissing,
  'believed_dead': MESSAGES.believedDead,
};

/**
 * A component which shows a single note record.
 *
 * Usage: <Note note={note} />
 */
class Note extends Component {
  renderStatus() {
    return <FormattedMessage {...STATUS_MESSAGES[this.props.note.status]} />;
  }

  render() {
    return (
      <Card className='note-card'>
        {/* TODO(gimite): Add drop down menu. */}
        <div className='note-section'>
          <div className='note-headline'>
            <div className='note-headlinephoto'>
              <img src={this.props.note.photo_url} />
            </div>
            <div className='note-headlinecontent'>
              <h5 className='mdc-typography--subtitle2'>
                <FormattedMessage
                  {...MESSAGES.postedBy}
                  values={{authorName: this.props.note.author_name}}
                />
              </h5>
              <p className='mdc-typography--caption'>
                {this.props.note.source_date}
              </p>
            </div>
          </div>
        </div>

        <div className='note-section'>
          <div className='mdc-typography--body2'>
            {this.props.note.text}
          </div>
          <div className='mdc-typography--caption'>
            <div>
              <FormattedMessage {...MESSAGES.status} />:
              <span> </span>
              {this.renderStatus()}
            </div>
            {this.props.note.author_made_contact ?
              <div><FormattedMessage {...MESSAGES.authorMadeContact} /></div>
              : null
            }
            {this.props.note.last_known_location ?
              <div>
                <FormattedMessage {...MESSAGES.lastKnownLocation} />:
                <span> </span>
                {this.props.note.last_known_location}
                <span> ・ </span>
                {/* TODO(gimite): Implement this. */}
                <a href='#'><FormattedMessage {...MESSAGES.map} /></a>
              </div>
              : null
            }
            {/* TODO(gimite): Add location */}
          </div>
        </div>
      </Card>
    );
  }
}

export default injectIntl(Note);
