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

  load_language_api();
}

// Loads the google language API to translate notes
function load_language_api() {
  if (typeof(google) != "undefined") {
    google.load("language", "1", {callback: translate_label});
  }  
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

// Translates the "Translated Message: " label
function translate_label() {
  google.language.translate('Translated message:', 'en', lang, translate_notes);
}

// Translate the note message
var translated_label;
function translate_notes(result) {
  if (!google.language.isTranslatable(lang)) {
    // Try "fr" if "fr-CA" doesn't work
    lang = lang.slice(0, 2);
    if (!google.language.isTranslatable(lang)) {
      return;
    }
  }

  var note_nodes = document.getElementsByName("note_text");
  translated_label = result.translation;

  for (var i = 0; i < note_nodes.length; i++) {
    // Set element id so it can be found later
    note_nodes[i].id = "note_msg" + i;
    google.language.translate(
        note_nodes[i].firstChild.innerHTML, "", lang,
        translated_callback_closure(i));
  }
}

function translated_callback_closure(i) {
  return function(result) {
    translated_callback(result, i);
  };
}

function translated_callback(result, i) {
  if (!result.translation) {
    return;
  }

  if (result.detectedSourceLanguage == lang) {
    return;
  }
  // Have to parse to Int to translate from unicode for
  // arabic, japanese etc...
  document.getElementById("note_msg" + i).innerHTML +=
      '<div class="translation">' + translated_label + ' ' +
      result.translation + '</div>';
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
