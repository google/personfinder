import React from "react";
import {injectIntl} from 'react-intl';
import {BrowserRouter, Route} from "react-router-dom";

import AddPerson from "./AddPerson.js";
import GlobalHome from "./GlobalHome.js";
import RepoHome from "./RepoHome.js";
import RepoResults from "./RepoResults.js";
import View from "./View.js";

const App = () => (
  <BrowserRouter>
    <div>
      <Route exact path="/" component={GlobalHome} />
      <Route exact path="/:repoId" component={RepoHome} />
      <Route exact path="/:repoId/create" component={AddPerson} />
      <Route exact path="/:repoId/results" component={RepoResults} />
      <Route exact path="/:repoId/view" component={View} />
    </div>
  </BrowserRouter>
);

export default injectIntl(App);
