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
