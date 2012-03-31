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

function $(id) {
  return document.getElementById(id);
}

// Dynamic behavior for the Person entry form.
function update_clone() {
  var display_original = $('clone_no').checked ? 'inline' : 'none';
  var display_clone = $('clone_yes').checked ? 'inline' : 'none';
  var display_source = $('clone_yes').checked ? '' : 'none';

  $('author_name_original').style.display = display_original;
  $('author_phone_original').style.display = display_original;
  $('author_email_original').style.display = display_original;
  $('author_name_clone').style.display = display_clone;
  $('author_phone_clone').style.display = display_clone;
  $('author_email_clone').style.display = display_clone;
  $('source_url_row').style.display = display_source;
  $('source_date_row').style.display = display_source;
  $('source_name_row').style.display = display_source;
}

//Dynamic behavior for the Note entry form.
function update_contact() {
  var display_contact = $('found_yes').checked ? '' : 'none';
  $('contact_row').style.display = display_contact;
}

//Dynamic behavior for the image url / upload entry fields.
function update_image_input() {
  var upload = $('photo_upload_radio').checked;
  if (upload) {
    $('photo_upload').disabled = false;
    $('photo_upload').focus();
    $('photo_url').disabled = true;
  } else {
    $('photo_upload').disabled = true;
    $('photo_url').disabled = false;
    $('photo_url').focus();
  }
}

// Sends a single request to the Google Translate API.
var translate_callback_id = 0;
function translate(source, target, text, continuation) {
  var callback = 'translate_callback_' + (++translate_callback_id);
  window[callback] = continuation;
  var script = document.createElement('script');
  script.src = 'https://www.googleapis.com/language/translate/v2' +
      '?key=' + encodeURIComponent(translate_api_key) +
      (source ? '&source=' + encodeURIComponent(source) : '') +
      '&target=' + encodeURIComponent(target) +
      '&callback=' + encodeURIComponent(callback) +
      '&q=' + encodeURIComponent(text);
  document.getElementsByTagName('head')[0].appendChild(script);
}

// Translates the contents of all the notes.
function translate_notes(result) {
  function get_translation_result(result) {
    return result && result.data && result.data.translations &&
        result.data.translations[0] &&
        result.data.translations[0].translatedText;
  }

  // The label "Translated message:", translated into the user's language.
  var label = get_translation_result(result);
  if (label) {
    var elements = document.getElementsByName("note_text");
    for (var i = 0; i < elements.length; i++) {
      (function(element) {
        translate('', lang, element.innerHTML, function(result) {
          var message = get_translation_result(result);
          if (message) {
            var text = label + ' ' + message;
            var html = text.replace('&', '&amp;').replace('<', '&lt;');
            element.innerHTML += '<div class="translation">' + html + '</div>';
          }
        });
      })(elements[i].firstChild);
    }
  }
}

// Invoked as an onload handler by create.py, multiview.py, and view.py.
function view_page_loaded() {
  // Hack for making a 'yes' selection persist in Google Chrome on going back.
  if ($('found_no')) {
    if (!$('found_no').checked) {
      $('found_yes').checked = true;
      update_contact();
    }
  }

  // Shows input fields for copied record when clone_yes is checked.
  if ($('clone_yes')) {
    if ($('clone_yes').checked) {
      update_clone();
    }
  }

  // Before translating the notes themselves, translate the label that
  // will go in front of each translated note.  This initial request also
  // serves as a test that the user's target language is supported.
  translate('en', lang, 'Translated message:', translate_notes);
}

// Selected people in duplicate handling mode.
var checked_ids = {};

// Initialize JavaScript state based on hidden fields.
function init_dup_state() {
  var dup_mode_enabled = $('dup_state').value == 'true';
  set_dup_mode(dup_mode_enabled, true);
}

// Switched duplicate handling UI on or off.
function set_dup_mode(enable, init) {
  $('dup_on_link').style.display = enable ? 'none' : '';
  $('dup_off_link').style.display = enable ? '' : 'none';
  $('dup_form').style.display = enable ? '' : 'none';
  $('dup_state').value = enable;
  
  var elems = document.getElementsByTagName('input');
  for (var i = 0; i < elems.length; ++i) {
    var elem = elems[i];
    if (elem.type.toLowerCase() == 'checkbox' && elem.name == 'dup') {
      elem.style.display = enable ? 'block' : 'none';
      if (init) {
        check_dup(elem);
      } else {
        elem.checked = false;
      }
    }
  }
  if (!init) {
    checked_ids = {};
    $('dup_count').innerHTML = '0';
    $('dup_go').disabled = true;
  }
  return false;
}

// Handles checking / unchecking a person for duplicate handling.
function check_dup(elem) {
  if (elem.checked) {
    checked_ids[elem.value] = true;
  } else {
    delete checked_ids[elem.value];
  }
  var count = 0;
  for (prop in checked_ids) {
    ++count;
  }
  $('dup_count').innerHTML = count;
  $('dup_go').disabled = (count < 2 || count > 3);
}

// Before submit, collect IDs for duplicate marking.
function mark_dup() {
  var ind = 0;
  for (prop in checked_ids) {
    $('id' + (++ind)).value = prop;
    if (ind == 3) {
      break;
    }
  }
}

// Returns true if the contents of the form are okay to submit.
function validate_fields() {
  // Check that mandatory fields are filled in.
  var mandatory_fields = ['first_name', 'last_name', 'text', 'author_name'];
  for (var i = 0; i < mandatory_fields.length; i++) {
    field = $(mandatory_fields[i]);
    if (field != null && field.value.length == 0) {
      $('mandatory_field_missing').setAttribute('style', '');
      field.focus();
      return false;
    }
  }
  $('mandatory_field_missing').setAttribute('style', 'display: none');

  // Check that the status and found values are not inconsistent.
  if ($('status').value == 'is_note_author' && $('found_no').checked) {
    $('status_inconsistent_with_found').setAttribute('style', '');
    return false;
  }
  
  $('status_inconsistent_with_found').setAttribute('style', 'display: none');
  return true;
}
