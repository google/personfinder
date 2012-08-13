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

function show(element) {
  if (element) {
    element.style.display = '';
  }
}

function hide(element) {
  if (element) {
    element.style.display = 'none';
  }
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

// Dynamic behavior for the Note entry form.
function update_contact() {
  var display_contact = $('author_made_contact_yes').checked ? '' : 'none';
  $('contact_row').style.display = display_contact;
}

// Dynamic behavior for the image URL / upload entry fields.
// If for_note is true, target fields in the Note entry form; otherwise target
// fields in the Person entry form.
function update_image_input(for_note) {
  var id_prefix = for_note ? 'note_' : '';
  var upload = $(id_prefix + 'photo_upload_radio').checked;
  if (upload) {
    $(id_prefix + 'photo_upload').disabled = false;
    $(id_prefix + 'photo_upload').focus();
    $(id_prefix + 'photo_url').disabled = true;
  } else {
    $(id_prefix + 'photo_upload').disabled = true;
    $(id_prefix + 'photo_url').disabled = false;
    $(id_prefix + 'photo_url').focus();
  }
}

// Shows a new text field for a profile URL.
function add_profile_entry(select) {
  function set_profile_website(entry_index, website_index) {
    $('profile_website_index' + entry_index).value = website_index;

    // First remove the existing icon if any.
    icon_container = $('profile_icon' + entry_index);
    icon_container.innerHTML = '';

    var profile_website = profile_websites[profile_website_index];
    if (profile_website) {
      var icon = document.createElement('img');
      icon.src = profile_website.icon_url;
      icon_container.appendChild(icon);
    }
  }

  var profile_website_index = select.selectedIndex - 1;
  select.selectedIndex = 0;

  var added = false;
  var can_add_more = false;
  for (var i = 1, entry; entry = $('profile_entry' + i); ++i) {
    if (entry.style.display == 'none') {
      if (!added) {
        set_profile_website(i, profile_website_index);
        show(entry);
        added = true;
      } else {
        can_add_more = true;
      }
    }
  }

  if (!can_add_more) {
    hide($('add_profile_entry'));
  }
}

// Hides one of the profile page input fields specified by the index of the
// corresponding <tr> element, and shows the add_profile_entry link if hidden.
function close_profile_entry(profile_entry_index) {
  $('profile_entry' + profile_entry_index).style.display = 'none';
  $('profile_url' + profile_entry_index).value = '';
  show($('add_profile_entry'));
}

// Toggles the state of controls for adding a new profile entry.
// 'add': shows 'Add another profile page' link.
// 'select': shows a drop down list to select a profile website to add.
// 'close': closes the whole controls.
function toggle_add_profile_entry_controls(state) {
  if (state == 'add') {
    show($('add_profile_entry'));
    hide($('add_profile_entry_select'));
    show($('add_profile_entry_link'));
  } else if (state == 'select') {
    show($('add_profile_entry'));
    $('add_profile_entry_select').selectedIndex = 0;
    show($('add_profile_entry_select'));
    hide($('add_profile_entry_link'));
  } else if (state == 'close') {
    hide($('add_profile_entry'));
  }
}

// Sends a single request to the Google Translate API.  If the API returns a
// successful result, the continuation is called with the source language,
// target language, and translated text.
var translate_callback_id = 0;
function translate(source, target, text, continuation) {
  if (source === target) {
    // The Translate API considers 'en -> en' an invalid language pair,
    // so we add a shortcut for this special case.
    continuation(source, target, text);
  } else {
    // Set up a callback to extract the result from the Translate API response.
    var callback = 'translate_callback_' + (++translate_callback_id);
    window[callback] = function(response) {
      var result = response && response.data && response.data.translations &&
          response.data.translations[0];
      if (result) {
        source = result.detectedSourceLanguage || source;
        continuation(source, target, result.translatedText);
      } else if (target.length > 2) {
        // Try falling back to "fr" if "fr-CA" didn't work.
        translate(source, target.slice(0, 2), text, continuation);
      }
    };
    // Add a <script> tag to make a request to the Google Translate API.
    var script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = 'https://www.googleapis.com/language/translate/v2' +
        '?key=' + encodeURIComponent(translate_api_key) +
        (source ? '&source=' + encodeURIComponent(source) : '') +
        '&target=' + encodeURIComponent(target) +
        '&callback=' + encodeURIComponent(callback) +
        '&q=' + encodeURIComponent(text);
    document.getElementsByTagName('head')[0].appendChild(script);
  }
}

// Translates the contents of all the notes.  The 'label' argument is
// the label "Translated message:", translated into the user's language.
function translate_notes(source, target, label) {
  var elements = document.getElementsByName("note_text");
  for (var i = 0; i < elements.length; i++) {
    (function(element) {
      translate('', lang, element.innerHTML, function(source, target, text) {
        if (source !== target) {
          var html = (label + ' ' + text).replace('&', '&amp;')
              .replace('<', '&lt;').replace('>', '&gt;');
          element.innerHTML += '<div class="translation">' + html + '</div>';
        }
      });
    })(elements[i].firstChild);
  }
}

// Invoked as an onload handler by create.py, multiview.py, and view.py.
function view_page_loaded() {
  // Hack for making a 'yes' selection persist in Google Chrome on going back.
  if ($('author_made_contact_no')) {
    if (!$('author_made_contact_no').checked) {
      $('author_made_contact_yes').checked = true;
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
  if (translate_api_key) {
    translate('en', lang, 'Translated message:', translate_notes);
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

// Returns true if the contents of the form are okay to submit.
function validate_fields() {
  // Check that mandatory fields are filled in.
  var mandatory_fields = ['given_name', 'family_name', 'text', 'author_name'];
  for (var i = 0; i < mandatory_fields.length; i++) {
    field = $(mandatory_fields[i]);
    if (field != null && field.value.match(/^\s*$/)) {
      $('mandatory_field_missing').setAttribute('style', '');
      field.focus();
      return false;
    }
  }
  $('mandatory_field_missing').setAttribute('style', 'display: none');

  // Check that the status and author_made_contact values are not inconsistent.
  if ($('status') && $('status').value == 'is_note_author' &&
      $('author_made_contact_no') && $('author_made_contact_no').checked) {
    $('status_inconsistent_with_author_made_contact').setAttribute('style', '');
    return false;
  }
  $('status_inconsistent_with_author_made_contact')
      .setAttribute('style', 'display: none');

  // Check profile_urls
  for (var i = 1, entry; entry = $('profile_entry' + i); ++i) {
    if (entry.style.display != 'none') {
      var url = $('profile_url' + i).value;
      var website_index = parseInt($('profile_website_index' + i).value);
      var url_regexp = profile_websites[website_index].url_regexp;
      if (!url.match(url_regexp)) {
        $('invalid_profile_url').setAttribute('style', '');
        $('profile_url' + i).focus();
        return false;
      }
    }
  }
  $('invalid_profile_url').setAttribute('style', 'display: none');

  return true;
}
