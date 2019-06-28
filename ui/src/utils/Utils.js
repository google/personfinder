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

import queryString from 'query-string';

/*
 * A class for utility functions.
 */
class Utils {

  static getURLParam(props, paramName) {
    return queryString.parse(props.location.search)[paramName];
  }

  static onExternalScriptLoad(url) {
    EXTERNAL_SCRIPTS[url].loaded = true;
    const callbacksList = EXTERNAL_SCRIPTS[url].callbacks;
    for (var i = 0; i < callbacksList.length; i++) {
      callbacksList[i]();
    }
  }

  static loadExternalScript(url, callback) {
    if (EXTERNAL_SCRIPTS[url] == undefined) {
      EXTERNAL_SCRIPTS[url] = {callbacks: [callback], loaded: false};
      const scriptTag = document.createElement('script');
      scriptTag.src = url;
      scriptTag.addEventListener(
          'load', () => Utils.onExternalScriptLoad(url));
      document.getElementsByTagName('body')[0].appendChild(scriptTag);
    } else if (EXTERNAL_SCRIPTS[url].loaded) {
      callback();
    } else {
      EXTERNAL_SCRIPTS[url].callbacks.push(callback);
    }
  }
}

export default Utils;
