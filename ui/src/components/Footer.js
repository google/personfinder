import React, {Component} from 'react';
import {FormattedMessage, defineMessages, injectIntl} from 'react-intl';

const messages = defineMessages({
  disclaimerText: {
    id: 'Footer.disclaimerText',
    defaultMessage: ('PLEASE NOTE: all data entered is available to the public '
        + 'and usable by anyone. Google does not review or verify the accuracy '
        + 'of this data. Google may share the data with public and private '
        + 'organizations participating in disaster response efforts.'),
    description: 'A disclaimer shown at the footer of the page.',
  },
});

class Footer extends Component {
  render() {
    return (
      <div className="footer">
        <p className="mdc-typography--body1">
          <FormattedMessage {...messages.disclaimerText} />
        </p>
      </div>
    );
  }
}

export default injectIntl(Footer);
