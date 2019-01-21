import React, {Component} from 'react';

/**
 * A component for wrapping something in a notched outline.
 *
 * We may be able to get rid of this at some point and use a component built by
 * the Material team, but a) the documentation for the React NotchedOutline is
 * pretty sparse and b) I'm not sure Material supports using their
 * NotchedOutline with anything other than TextField and Select components.
 */
class PFNotchedOutline extends Component {
  render() {
    return (
      <div className='pf-notchedoutline'>
        <label className='mdc-typography--body1 pf-notchedoutline-label'>
          {this.props.label}
        </label>
        <div className='pf-notchedoutline-content'>{this.props.children}</div>
      </div>
    );
  }
}

export default PFNotchedOutline;
