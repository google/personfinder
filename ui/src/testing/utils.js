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
