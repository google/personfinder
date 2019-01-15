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

import Footer from "./../components/Footer.js";

const messages = defineMessages({
  developers: {
    id: 'GlobalHome.developers',
    defaultMessage: 'Developers',
    description: ('A header for a section about how software developers can '
        + 'use the product to help with a disaster response.'),
  },
  developersHowToHelp: {
    id: 'GlobalHome.developersHowToHelp',
    defaultMessage: ('You can help continue to improve Google Person Finder:'
        + '<ul><li>Learn about the PFIF data model</li><li>Customize or '
        + 'improve Person Finder</li></ul>'),
    description: ('A summary of how software developers can help improve the '
        + 'product.'),
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
  productNameWithEmphasis: {
    id: 'GlobalHome.productNameWithEmphasis',
    defaultMessage: '<b>Google</b> Person Finder',
    description: ('Name of the product. Person Finder is a tool that helps '
        + 'people reconnect with friends/family after a disaster.'),
  },
  responders: {
    id: 'GlobalHome.responders',
    defaultMessage: 'Responders',
    description: ('A header for a section about how disaster responders, such '
        + 'local officials, nonprofit organizations, etc., can use the product '
        + 'to help.'),
  },
  respondersHowToHelp: {
    id: 'GlobalHome.respondersHowToHelp',
    defaultMessage: ('You can help people find each other in the aftermath of '
        + 'a disaster:<ul><li>Embed Google Person Finder in your site</li>'
        + '<li>Download data from Google Person Finder</li><li>Upload data '
        + 'into Google Person Finder</li></ul>'),
    description: 'A summary of how response organizations can use the product.',
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

class GlobalHome extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoaded: false,
      error: null,
      repos: []
    };
  }

  componentDidMount() {
    fetch("/global/d/repoinfo")
      .then(res => res.json())
      .then(
        (repos) => {
          for (var i = 0; i < repos.length; i++) {
            repos[i]['displayCat'] = i % 5;
          }
          this.setState({
            isLoaded: true,
            repos: repos
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

  renderHeader() {
    return (
      <div>
        <h1 className="mdc-typography--headline1">
          <img src="/static/icons/maticon_person_pin.svg" />
          <FormattedHTMLMessage {...messages.productNameWithEmphasis} />
        </h1>
        <p className="mdc-typography--body1 globalhome-headerdesc">
          <FormattedMessage {...messages.tagline} />
        </p>
        <Button
          className="pf-button-secondary globalhome-howsitworkbutton"
          raised
          onClick={() => console.log('clicked!')}
        >
          {this.props.intl.formatMessage(messages.howDoesItWork)}
        </Button>
      </div>
    );
  }

  renderRespondersCard() {
    return (
      <Card className="globalhome-thirdpartycard">
        <div>
          <h3 className="mdc-typography--headline3">
            <FormattedMessage {...messages.responders} />
          </h3>
          <p className="mdc-typography--body1">
            <FormattedHTMLMessage {...messages.respondersHowToHelp} />
          </p>
        </div>
        <CardActions>
          <CardActionButtons>
            <Button
              className="pf-button-secondary"
              raised
              onClick={() => console.log('clicked!')}
            >
              {this.props.intl.formatMessage(messages.learnHow)}
            </Button>
          </CardActionButtons>
        </CardActions>
      </Card>
    );
  }

  renderDevelopersCard() {
    return (
      <Card className="globalhome-thirdpartycard">
        <div>
          <h3 className="mdc-typography--headline3">
            <FormattedMessage {...messages.developers} />
          </h3>
          <p className="mdc-typography--body1">
            <FormattedHTMLMessage {...messages.developersHowToHelp} />
          </p>
        </div>
        <CardActions>
          <CardActionButtons>
            <Button
              className="pf-button-secondary"
              raised
              onClick={() => console.log('clicked!')}
            >
              {this.props.intl.formatMessage(messages.getStarted)}
            </Button>
          </CardActionButtons>
        </CardActions>
      </Card>
    );
  }

  renderThirdPartyHelpCards() {
    return (
      <div className="globalhome-thirdpartywrapper">
        <div className="endbars-headerline-wrapper" dir="ltr">
          <span className="mdc-typography--overline endbars-headerline">
            <FormattedMessage {...messages.youCanHelp} />
          </span>
        </div>
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
    var cells = this.state.repos.map(repo => (
      <Cell key={repo.repoId}>
        <RepoCard repoInfo={repo} />
      </Cell>
    ));
    return <Grid><Row>{cells}</Row></Grid>;
  }

  render() {
    if (this.state.error) {
      return <div>An error occurred</div>
    }
    if (!this.state.isLoaded) {
      return <div>Loading...</div>;
    }
    return (
      <div className="globalhome-wrapper">
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

const repoCardMessages = defineMessages({
  repoRecordCount: {
    id: 'RepoCard.repoRecordCount',
    defaultMessage: 'Tracking {recordCount} records.',
    description: ('A message displaying how many data records we have in the '
        + 'database.'),
  },
});

class RepoCardImpl extends Component {
  constructor(props) {
    super(props);
    this.goTo = this.goTo.bind(this);
  }

  goTo() {
    this.props.history.push("/" + this.props.repoInfo.repoId);
  }

  render() {
    var repocardImageClassName = (
        "repocard-image repocard-imagedisplaycat" +
        this.props.repoInfo.displayCat);
    var recordCountContent = null;
    if (this.props.repoInfo.recordCount > 0) {
      recordCountContent = (
        <p className="mdc-typography--body1 repocard-recordcount">
          <FormattedMessage
            {...repoCardMessages.repoRecordCount }
            values={{
              "recordCount": this.props.repoInfo.recordCount
            }} />
        </p>
      );
    }
    return (
      <Card className="repocard">
        <CardPrimaryContent className="repocard-content" onClick={this.goTo}>
          <div className={repocardImageClassName}>
            <p className="mdc-typography--body1">
              {this.props.repoInfo.title[0]}
            </p>
          </div>
          <div className="repocard-info">
            <h5 className="mdc-typography--headline5 repocard-title">
              {this.props.repoInfo.title}
            </h5>
            {recordCountContent}
          </div>
        </CardPrimaryContent>
      </Card>
    );
  }
}

const RepoCard = withRouter(injectIntl(RepoCardImpl));

export default injectIntl(GlobalHome);
