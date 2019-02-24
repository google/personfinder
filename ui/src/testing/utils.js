/**
 * A utility function to help run unit tests for page components.
 *
 * runPageTest will first call setupFunc to set up the page component, which is
 * expected to return an array of two items: the Enzyme wrapper and any data
 * that the test function needs. Next, runPageFunc will call update() on the
 * Enzyme wrapper, and then call the testFunc with wrapper and the data from
 * setupFunc. Lastly, it will unmount the wrapper and call the doneFunc to clean
 * up.
 *
 * @param {function} doneFunc - The done function from Jest.
 * @param {function} setupFunc - A function to set up the component under test.
 * Should return an array of two items: the Enzyme wrapper for the page
 * component, and any data the test function needs.
 * @param {function} testFunc - A function to test the component. Will be passed
 * two parameters: the Enzyme wrapper, and the other data returned from the
 * setup function.
 */
export function runPageTest(doneFunc, setupFunc, testFunc) {
  const [wrapper, data] = setupFunc();
  setImmediate(() => {
    wrapper.update();
    testFunc(wrapper, data);
    wrapper.unmount();
    doneFunc();
  });
}
