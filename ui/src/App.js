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
import {injectIntl} from 'react-intl';
import {BrowserRouter, Redirect, Route} from 'react-router-dom';

import Create from './pages/Create.js';
import GlobalHome from './pages/GlobalHome.js';
import RepoHome from './pages/RepoHome.js';
import Results from './pages/Results.js';
import View from './pages/View.js';

import './css/all.scss';

const App = () => (
  <BrowserRouter>
    <div>
      <Route exact path='/' component={GlobalHome} />
      <Route exact path='/:repoId' component={RepoHome} />
      <Route exact path='/:repoId/create' component={Create} />
      <Route exact path='/:repoId/results' component={Results} />
      <Route exact path='/:repoId/view' component={View} />
      <Route exact path='/global/home.html' render={() => (
            <Redirect to='/'/>
          )}/>
    </div>
  </BrowserRouter>
);

export default injectIntl(App);
