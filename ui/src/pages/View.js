import React, {Component} from 'react';
import {FormattedMessage, defineMessages, injectIntl} from 'react-intl';

import LoadingIndicator from "./../components/LoadingIndicator.js";

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
    const personId = new URL(window.location.href).searchParams.get("id");
    // TODO(nworden): consider if we could have a global cache of repo info to
    // avoid calling for it on each page load
    var apiCalls = [
        "/" + this.props.match.params.repoId + "/d/repoinfo",
        "/" + this.props.match.params.repoId + "/d/personinfo?id=" + personId,
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
