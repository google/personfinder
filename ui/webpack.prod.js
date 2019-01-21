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

/*
 * This file is for the prod Webpack config. It produces compiled JS bundles for
 * each of the languages Person Finder supports, with filenames in the form
 * <language code>-bundle.js (e.g., es-bundle.js).
 */

const merge = require('webpack-merge');
const webpack = require('webpack');

const common = require('./webpack.common.js');

// TODO(nworden): add the rest of the languages we support
const LANGS = ['en', 'es'];

module.exports = LANGS.map((lang) => {
  return merge(common, {
    name: lang + '-bundle',
    mode: 'production',
    output: {
      filename: lang + '-bundle.[name]',
    },
    plugins: [
      new webpack.DefinePlugin({
        'BUNDLE_LANGUAGE': JSON.stringify(lang),
      }),
    ],
  });
});
