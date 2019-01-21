import React, {Component} from 'react';
import {FormattedHTMLMessage, defineMessages, injectIntl} from 'react-intl';
import {Link} from "react-router-dom";

const messages = defineMessages({
  productName: {
    id: 'RepoHeader.productName',
    defaultMessage: 'Google Person Finder',
    description: ('Name of the product. Person Finder is a tool that helps '
        + 'people reconnect with friends/family after a disaster.'),
  },
});

class RepoHeader extends Component {
  render() {
    return (
      <div id="repoheader">
        <div id="repoheader-backbutton">
          <Link to={"/" + this.props.repoInfo.repoId}>
            <div><img src="/static/icons/maticon_arrow_back.svg" /></div>
          </Link>
        </div>
        <div id="repoheader-info">
          <p className="mdc-typography--subtitle1">
            <FormattedHTMLMessage {...messages.productName} />
          </p>
          <p className="mdc-typography--subtitle2">
            {this.props.repoInfo.title}
          </p>
        </div>
      </div>
    );
  }
}

export default injectIntl(RepoHeader);
