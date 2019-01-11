import React from "react";
import ReactDOM from "react-dom";
import {addLocaleData, IntlProvider} from 'react-intl';

import App from "./App.js";

addLocaleData(require('react-intl/locale-data/' + BUNDLE_LANGUAGE));

ReactDOM.render(
    <IntlProvider
        locale={BUNDLE_LANGUAGE}
        messages={require('./translations/' + BUNDLE_LANGUAGE + '.js')}>
      <App />
    </IntlProvider>,
    document.getElementById("root"));
