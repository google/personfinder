// Copyright 2010 Google Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Activation of the Google Virtual Keyboard element.  To use this, call
// initialize_keyboard with the name of a keyboard layout constant after
// the document has finished loading.

google.load("elements", "1", {packages: "keyboard"});

var keyboard;
var keyboard_first_click = true;

function initialize_keyboard(layout_code) {
  var show_keyboard = false;

  var textareas = document.getElementsByTagName('textarea');
  for (var i = 0; i < textareas.length; i++) {
    add_listener('click', textareas[i], set_keyboard_visible);
    show_keyboard = true;
  }

  var inputs = document.getElementsByTagName('input');
  for (var i = 0; i < inputs.length; i++) {
    if (inputs[i].type == 'text') {
      add_listener('click', inputs[i], set_keyboard_visible);
      show_keyboard = true;
    }
  }

  if (show_keyboard) {
    keyboard = new google.elements.keyboard.Keyboard(
      [google.elements.keyboard.LayoutCode[layout_code]]);
    setTimeout(function() { keyboard.setVisible(false); }, 250);
  }
}

function set_keyboard_visible() {
  if (keyboard && keyboard_first_click) {
    keyboard.setVisible(true);
    keyboard_first_click = false;
  }
}

function add_listener(event, element, callback) {
  if (element.addEventListener) {
    return element.addEventListener(event, callback, false);
  } else if (element.attachEvent) {
    return element.attachEvent("on" + event, callback);
  }
}

