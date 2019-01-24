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

import React from 'react';

/*
 * A component for headers with bars on the ends.
 *
 * They look something like this:
 *      ----- Title or whatever -----
 */
const EndBarHeader = (props) => (
  <div className='endbars-headerline-wrapper' dir='ltr'>
    <span className='mdc-typography--overline endbars-headerline'>
      {props.children}
    </span>
  </div>
);

export default EndBarHeader;
