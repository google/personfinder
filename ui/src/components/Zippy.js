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

/*
 * A component for a zippy section.
 */
class Zippy extends Component {
  render() {
    const content = this.props.display ?
        <p>{this.props.children}</p> : null;
    return (
      <div>
        <div className='zippy-header'>
          <a onClick={() => this.props.zipHandler(!this.props.display)}>
            {this.props.header}
          </a>
        </div>
        {content}
      </div>
    );
  }
}

export default Zippy;
