const merge = require('webpack-merge');
const path = require('path');
const webpack = require('webpack');

const common = require('./webpack.common.js');

module.exports = merge(common, {
  mode: 'development',
  devServer: {
    contentBase: path.join(__dirname, 'static/'),
    proxy: {
      '/*/d/**': {
        target: 'http://localhost:8000',
        secure: false
      }
    },
    port: 3000,
    publicPath: 'http://localhost:3000/dist/',
    historyApiFallback: true,
    hotOnly: true
  },
  plugins: [
    new webpack.DefinePlugin({
      'BUNDLE_LANGUAGE': JSON.stringify('en'),
    }),
    new webpack.HotModuleReplacementPlugin(),
  ],
  output: {
    filename: 'dev-bundle.[name]',
  },
});
