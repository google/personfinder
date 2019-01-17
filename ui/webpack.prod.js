const merge = require('webpack-merge');
const webpack = require('webpack');

const common = require('./webpack.common.js');

/**
 * TODO(nworden): add the rest of the languages
 */
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
