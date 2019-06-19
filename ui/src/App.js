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
import {BrowserRouter, Route} from 'react-router-dom';

import AddNote from './pages/AddNote.js';
import Create from './pages/Create.js';
import GlobalHome from './pages/GlobalHome.js';
import HowToPage from './pages/HowToPage.js';
import RepoHome from './pages/RepoHome.js';
import RespondersPage from './pages/RespondersPage.js';
import Results from './pages/Results.js';
import View from './pages/View.js';

import './css/all.scss';

const App = () => (
  <BrowserRouter>
    <div>
      {/* TODO(nworden): include support for legacy homepage URL:
          global/home.html */}
      <Route exact path='/' component={GlobalHome} />
      <Route exact path='/global/howto' component={HowToPage} />
      <Route exact path='/global/responders' component={RespondersPage} />
      <Route exact path='/:repoId' component={RepoHome} />
      <Route exact path='/:repoId/add_note' component={AddNote} />
      <Route exact path='/:repoId/create' component={Create} />
      <Route exact path='/:repoId/results' component={Results} />
      <Route exact path='/:repoId/view' component={View} />
    </div>
  </BrowserRouter>
);

export default injectIntl(App);
