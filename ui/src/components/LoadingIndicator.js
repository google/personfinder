import React, {Component} from 'react';
import {FormattedMessage, defineMessages, injectIntl} from 'react-intl';

const messages = defineMessages({
  loading: {
    id: 'LoadingIndicator.loading',
    defaultMessage: 'Loading...',
    description: 'A message indicating to the user that the page is loading.',
  },
});

class LoadingIndicator extends Component {
  render() {
    return <FormattedMessage {...messages.loading} />
  }
}

export default injectIntl(LoadingIndicator);
