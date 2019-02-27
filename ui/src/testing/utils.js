/**
 * Returns a promise to run resolve after existing promises are flushed.
 *
 * Long story short, we can't properly test components until componentDidMount
 * has run, but, when componentDidMount has async calls (e.g., to fetch data and
 * then use it to set state), React/Enzyme leaves us without any good ways to
 * wait for componentDidMount. We use setImmediate to get around this.
 */
export function flushPromises() {
  return new Promise(setImmediate);
};
