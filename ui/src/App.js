import React from "react";
import {injectIntl} from 'react-intl';
import {BrowserRouter, Route} from "react-router-dom";

import Create from "./pages/Create.js";
import GlobalHome from "./pages/GlobalHome.js";
import RepoHome from "./pages/RepoHome.js";
import Results from "./pages/Results.js";
import View from "./pages/View.js";

import './css/all.scss';

const App = () => (
  <BrowserRouter>
    <div>
      /**
       * TODO(nworden): include support for legacy homepage URL: global/home.html
       */
      <Route exact path="/" component={GlobalHome} />
      <Route exact path="/:repoId" component={RepoHome} />
      <Route exact path="/:repoId/create" component={Create} />
      <Route exact path="/:repoId/results" component={Results} />
      <Route exact path="/:repoId/view" component={View} />
    </div>
  </BrowserRouter>
);

export default injectIntl(App);
