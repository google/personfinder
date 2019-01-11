const merge = require('webpack-merge');
const webpack = require('webpack');

const common = require('./webpack.common.js');

const LANGS = ['en', 'es'];

module.exports = LANGS.map(function(lang) {
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
