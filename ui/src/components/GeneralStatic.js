import React, { Component } from 'react';
import Footer from './Footer';

/**
 * General static component for rendering pages
 *
 * @class StaticComp
 * @extends {Component}
 */
const StaticPage = ({ subtitle, children }) => (
  <div className='staticpage-wrapper'>
    {/* TODO(nworden): Refactor repoheader and use it here */}
    <div id='repoheader-info'>
      <p className='mdc-typography--subtitle1'>{subtitle}</p>
    </div>
    <div className='staticpage-contents'>
      { children }
    </div>
    <Footer />
  </div>
);


export default StaticPage;
