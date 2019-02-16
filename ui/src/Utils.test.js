import Utils from './Utils.js';

test('Simple query param is parsed correctly.', () => {
  const props = {
    location: {
      search: '?spiderman=peterparker',
    },
  };
  expect(Utils.getURLParam(props, 'spiderman')).toBe('peterparker');
});

test('Multiple query params are parsed correctly.', () => {
  const props = {
    location: {
      search: '?spiderman=peterparker&superman=clarkkent',
    },
  };
  expect(Utils.getURLParam(props, 'spiderman')).toBe('peterparker');
  expect(Utils.getURLParam(props, 'superman')).toBe('clarkkent');
});

test('Returns undefined when query parameter is missing.', () => {
  const props = {
    location: {
      search: '?spiderman=peterparker&superman=clarkkent',
    },
  };
  expect(Utils.getURLParam(props, 'batman')).toBeUndefined();
});
