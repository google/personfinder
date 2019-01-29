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

/**
 * A component for wrapping something in a notched outline.
 *
 * We may be able to get rid of this at some point and use a component built by
 * the Material team, but a) the documentation for the React NotchedOutline is
 * pretty sparse and b) I'm not sure Material supports using their
 * NotchedOutline with anything other than TextField and Select components.
 *
 * @param {object} props
 */
const PFNotchedOutline = (props) => (
  <div className='pf-notchedoutline'>
    <label className='mdc-typography--body1 pf-notchedoutline-label'>
      {props.label}
    </label>
    <div className='pf-notchedoutline-content'>{props.children}</div>
  </div>
);

export default PFNotchedOutline;
