import React, {Component} from 'react';
import {FormattedHTMLMessage, FormattedMessage, defineMessages, injectIntl} from 'react-intl';
import Button from '@material/react-button';

import Footer from "./../components/Footer.js";
import LoadingIndicator from "./../components/LoadingIndicator.js";
import RepoHeader from "./../components/RepoHeader.js";
import SearchBar from "./../components/SearchBar.js";

const messages = defineMessages({
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
  repoRecordCount: {
    id: 'RepoHome.repoRecordCount',
    defaultMessage: 'Currently tracking {recordCount} records.',
    description: ('A message displaying how many data records we have in the '
        + 'database.'),
  },
});

class RepoHome extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isLoaded: false,
      error: null,
      repoInfo: null
    };
    this.goToAdd = this.goToAdd.bind(this);
    this.handleSearchFn = this.handleSearchFn.bind(this);
  }

  goToAdd() {
    this.props.history.push("/" + this.props.match.params.repoId + "/create");
  }

  handleSearchFn(query) {
    this.props.history.push({
        pathname: "/" + this.props.match.params.repoId + "/results",
        search: "?query_name=" + query,
      });
  }

  componentDidMount() {
    const apiUrl = "/" + this.props.match.params.repoId + "/d/repoinfo";
    fetch(apiUrl)
      .then(res => res.json())
      .then(
        (repoInfo) => {
          this.setState({
            isLoaded: true,
            repoInfo: repoInfo
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
    if (this.state.repoInfo.recordCount > 0) {
      recordCountContent = (
          <p className="mdc-typography--body1 repohome-recordcount">
            <FormattedMessage
              {...messages.repoRecordCount}
              values={{
                "recordCount": this.state.repoInfo.recordCount
              }} />
          </p>
      );
    }
    return (
      <div>
        <RepoHeader repoInfo={this.state.repoInfo} />
        <div className="repohome-body">
          <SearchBar
              repoId={this.props.match.params.repoId}
              initialValue=""
              handleSearchFn={this.handleSearchFn} />
          {recordCountContent}
          <div className="endbars-headerline-wrapper" dir="ltr">
            <span className="mdc-typography--overline endbars-headerline">
              <FormattedMessage {...messages.or} />
            </span>
          </div>
          <Button
            className="pf-button-secondary"
            raised
            onClick={this.goToAdd}
          >
            {this.props.intl.formatMessage(messages.provideInfoAboutSomeone)}
          </Button>
        </div>
        <Footer />
      </div>);
  }
}

export default injectIntl(RepoHome);
