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
import {FormattedHTMLMessage, FormattedMessage, defineMessages, injectIntl} from 'react-intl';
import {withRouter} from 'react-router-dom';
import Button from '@material/react-button';
import Card, {
  CardActions,
  CardActionButtons,
  CardPrimaryContent
} from '@material/react-card';
import {Cell, Grid, Row} from '@material/react-layout-grid';

import EndBarHeader from './../components/EndBarHeader.js';
import Footer from './../components/Footer.js';
import LoadingIndicator from './../components/LoadingIndicator.js';

const MESSAGES = defineMessages({
  developers: {
    id: 'GlobalHome.developers',
    defaultMessage: 'Developers',
    description: ('A header for a section about how software developers can '
        + 'use the product to help with a disaster response.'),
  },
  developersHowToHelpFirstLineHTML: {
    id: 'GlobalHome.developersHowToHelpFirstLine',
    defaultMessage: 'You can help continue to improve Google Person Finder:',
    description: ('Part of a description of what third-parties can do to help '
        + 'improve the product. Ends in a colon because it will be followed by '
        + 'a list'),
  },
  developersHowToHelpListHTML: {
    id: 'GlobalHome.developersHowToHelpList',
    defaultMessage: ('<ul><li>Learn about the PFIF data model</li><li>'
        + 'Customize or improve Person Finder</li></ul>'),
    description: ('A list of ways third-party software developers can do to '
        + 'help improve the product. PFIF stands for Person Finder Interchange '
        + 'Format (a data standard for exhanging information about missing '
        + 'people).'),
  },
  getStarted: {
    id: 'GlobalHome.getStarted',
    defaultMessage: 'Get started',
    description: ('Label on a button that takes users to a page explaining how '
        + 'third-party developers can help.'),
  },
  howDoesItWork: {
    id: 'GlobalHome.howDoesItWork',
    defaultMessage: 'How does it work?',
    description: ('Label on a button that takes users to a page explaining how '
        + 'the product works.'),
  },
  learnHow: {
    id: 'GlobalHome.learnHow',
    defaultMessage: 'Learn how',
    description: ('Label on a button that takes users to a page explaining how '
        + 'third-party responders can help.'),
  },
  pfLogo: {
    id: 'GlobalHome.pfLogo',
    defaultMessage: 'Person Finder logo',
    description: 'Alt text for a logo image.',
  },
  productNameWithEmphasis: {
    id: 'GlobalHome.productNameWithEmphasis',
    defaultMessage: '<b>Google</b> Person Finder',
    description: ('Name of the product. Person Finder is a tool that helps '
        + 'people reconnect with friends/family after a disaster.'),
  },
  repoRecordCount: {
    id: 'GlobalHome.repoRecordCount',
    defaultMessage: 'Tracking {recordCount} records',
    description: ('A message displaying how many data records we have in the '
        + 'database.'),
  },
  responders: {
    id: 'GlobalHome.responders',
    defaultMessage: 'Responders',
    description: ('A header for a section about how disaster responders, such '
        + 'local officials, nonprofit organizations, etc., can use the product '
        + 'to help.'),
  },
  respondersHowToHelpFirstLineHTML: {
    id: 'GlobalHome.respondersHowToHelpFirstLine',
    defaultMessage: ('You can help people find each other in the aftermath of '
        + 'a disaster:'),
    description: ('Part of a description of how third-party organizations can '
        + 'use the product. Ends with a colon because it will be followed by a '
        + 'list.'),
  },
  respondersHowToHelpListHTML: {
    id: 'GlobalHome.respondersHowToHelpList',
    defaultMessage: ('<ul><li>Embed Google Person Finder in your site</li><li>'
        + 'Download data from Google Person Finder</li><li>Upload data into '
        + 'Google Person Finder</li></ul>'),
    description: ('A list of ways third-party organizations can use the '
        + 'product.'),
  },
  tagline: {
    id: 'GlobalHome.tagline',
    defaultMessage: ('Reconnect with friends and loved ones in the aftermath '
        + 'of natural and humanitarian disasters.'),
    description: 'A one-line summary of what the product is for.',
  },
  youCanHelp: {
    id: 'GlobalHomePage.youCanHelp',
    defaultMessage: 'You can help',
    description: ('Header on a section describing how people can help.'),
  }
});

// This should be set to the number of categories in
// ui/src/css/pages/_GlobalHome.scss (the classes called
// repocard-imagedisplaycategory0, repocard-imagedisplaycategory1, etc.).
const NUMBER_OF_DISPLAY_CATEGORY_COLORS = 5;

class GlobalHome extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoaded: false,
      error: null,
      repos: []
    };
    this.goToHowDoesItWork = this.goToHowDoesItWork.bind(this);
    this.goToRespondersPage = this.goToRespondersPage.bind(this);
    this.goToDevelopersPage = this.goToDevelopersPage.bind(this);
  }

  componentDidMount() {
    fetch('/global/d/repo')
      .then(res => res.json())
      .then(
        (repos) => {
          // We have multiple possible colors for the card backgrounds, and we
          // assign them to cards round-robin.
          repos.forEach((repo, i) =>
              repo.displayCategory = i % NUMBER_OF_DISPLAY_CATEGORY_COLORS);
          this.setState({
            isLoaded: true,
            repos: repos,
          });
        },
        (error) => {
          this.setState({
            isLoaded: true,
            error: error,
          });
        }
      );
  }

  goToHowDoesItWork() {
    this.props.history.push(`/global/howto`);
  }

  goToRespondersPage() {
    this.props.history.push(`/global/responders`);
  }

  goToDevelopersPage() {
    window.location.href = 'https://github.com/google/personfinder';
  }

  renderHeader() {
    return (
      <div>
        <h1 className='mdc-typography--headline1'>
          <img
              src='/static/icons/maticon_person_pin.svg'
              alt={this.props.intl.formatMessage(MESSAGES.pfLogo)} />
          <FormattedHTMLMessage {...MESSAGES.productNameWithEmphasis} />
        </h1>
        <p className='mdc-typography--body1 globalhome-headerdesc'>
          <FormattedMessage {...MESSAGES.tagline} />
        </p>
        {/* TODO(nworden): see if we can support right-click targets */}
        <Button
          className='pf-button-secondary globalhome-howsitworkbutton'
          outlined
          onClick={this.goToHowDoesItWork}
        >
          {this.props.intl.formatMessage(MESSAGES.howDoesItWork)}
        </Button>
      </div>
    );
  }

  renderRespondersCard() {
    return (
      <Card className='globalhome-thirdpartycard' outlined>
        <div>
          <h3 className='mdc-typography--headline3'>
            <FormattedMessage {...MESSAGES.responders} />
          </h3>
          <p className='mdc-typography--body1'>
            <FormattedHTMLMessage
                {...MESSAGES.respondersHowToHelpFirstLineHTML} />
          </p>
          <p className='mdc-typography--body1'>
            <FormattedHTMLMessage {...MESSAGES.respondersHowToHelpListHTML} />
          </p>
        </div>
        <CardActions>
          <CardActionButtons>
            <Button
              className='pf-button-secondary'
              outlined
              onClick={this.goToRespondersPage}
            >
              {this.props.intl.formatMessage(MESSAGES.learnHow)}
            </Button>
          </CardActionButtons>
        </CardActions>
      </Card>
    );
  }

  renderDevelopersCard() {
    return (
      <Card className='globalhome-thirdpartycard' outlined>
        <div>
          <h3 className='mdc-typography--headline3'>
            <FormattedMessage {...MESSAGES.developers} />
          </h3>
          <p className='mdc-typography--body1'>
            <FormattedHTMLMessage
                {...MESSAGES.developersHowToHelpFirstLineHTML} />
          </p>
          <p className='mdc-typography--body1'>
            <FormattedHTMLMessage {...MESSAGES.developersHowToHelpListHTML} />
          </p>
        </div>
        <CardActions>
          <CardActionButtons>
            <Button
              className='pf-button-secondary'
              outlined
              onClick={this.goToDevelopersPage}
            >
              {this.props.intl.formatMessage(MESSAGES.getStarted)}
            </Button>
          </CardActionButtons>
        </CardActions>
      </Card>
    );
  }

  renderThirdPartyHelpCards() {
    return (
      <div className='globalhome-thirdpartywrapper'>
        <EndBarHeader>
          <FormattedMessage {...MESSAGES.youCanHelp} />
        </EndBarHeader>
        <Grid>
          <Row>
            <Cell desktopColumns={6}>{this.renderRespondersCard()}</Cell>
            <Cell desktopColumns={6}>{this.renderDevelopersCard()}</Cell>
          </Row>
        </Grid>
      </div>
    );
  }

  renderRepoList() {
    const cells = this.state.repos.map(repo => (
      <div className='globalhome-repolistitem' key={repo.repoId}>
        <RepoCard history={this.props.history} repo={repo} />
      </div>
    ));
    return <div className='globalhome-repolistwrapper'>{cells}</div>;
  }

  render() {
    if (this.state.error) {
      /* TODO(nworden): write a better (and i18n'd) error message */
      return <div>An error occurred</div>
    }
    if (!this.state.isLoaded) {
      return <LoadingIndicator />;
    }
    return (
      <div className='globalhome-wrapper'>
        {this.renderHeader()}
        {this.renderRepoList()}
        {this.renderThirdPartyHelpCards()}
        <Footer />
      </div>
    );
  }
}

/**
 * RepoCard is a component for a card in the repo list.
 */
class RepoCardImpl extends Component {
  constructor(props) {
    super(props);
    this.goToRepo = this.goToRepo.bind(this);
  }

  goToRepo() {
    this.props.history.push('/' + this.props.repo.repoId);
  }

  render() {
    let repocardImageClassName = (
        'repocard-image repocard-imagedisplaycategory' +
        this.props.repo.displayCategory);
    let recordCountContent = null;
    if (this.props.repo.recordCount > 0) {
      recordCountContent = (
        <p className='mdc-typography--body1 repocard-recordcount'>
          <FormattedMessage
            {...MESSAGES.repoRecordCount }
            values={{
              'recordCount': this.props.repo.recordCount
            }} />
        </p>
      );
    }
    return (
      <Card className='repocard' outlined>
        <CardPrimaryContent
            className='repocard-content'
            tabIndex='0'
            onClick={this.goToRepo}
            onKeyDown={(e) => {return e.keyCode != 13 || this.goToRepo()}}>
          <div className={repocardImageClassName}>
            <p className='mdc-typography--body1'>
              {Array.from(this.props.repo.title)[0]}
            </p>
          </div>
          <div className='repocard-info'>
            <h5 className='mdc-typography--headline5 repocard-title'>
              {this.props.repo.title}
            </h5>
            {recordCountContent}
          </div>
        </CardPrimaryContent>
      </Card>
    );
  }
}

const RepoCard = injectIntl(RepoCardImpl);

export default injectIntl(GlobalHome);
