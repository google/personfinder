import React, {Component} from 'react';
import {defineMessages, injectIntl} from 'react-intl';
import {withRouter} from 'react-router-dom';
import TextField, {HelperText, Input} from '@material/react-text-field';

const messages = defineMessages({
  searchForAPerson: {
    id: 'SearchBar.searchForAPerson',
    defaultMessage: 'Search for a person',
    description: 'Label on a form for searching for information about someone.',
  },
});

class SearchBar extends Component {
  constructor(props) {
    super(props);
    this.state = {
      value: (props.initialValue == null ? "" : props.initialValue)};
    this.handleKeyDown = this.handleKeyDown.bind(this);
  }

  handleKeyDown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      this.props.handleSearchFn(this.state.value);
    }
  }

  render() {
    return (
      <TextField
        label={this.props.intl.formatMessage(messages.searchForAPerson)}
        outlined
        className="searchbar"
      >
        <Input
          value={this.state.value}
          onKeyDown={this.handleKeyDown}
          onChange={(e) => this.setState({value: e.target.value})} />
      </TextField>
    );
  }
}

export default injectIntl(SearchBar);
