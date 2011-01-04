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

// Hack for making the yes button not disappear on Google Chrome on go back.
function view_page_loaded() {
  if (!$('found_no').checked) {
    $('found_yes').checked = true;
    update_contact();
  }
  
  //event handler for the notification button
  var subscribe_btn = $('subscribe_btn');
  if (subscribe_btn != undefined) {
    $('subscribe_btn').onclick = function() {
  	  $('subscribe_label').style.display = 'block';
      $('email_subscr').style.display = 'block';
      $('subscribe_submit').style.display = 'block';
      $('subscribe_btn').style.display = 'none';
    }
  }  
}

function set_notification_trigger() {
  var email_subscr = $('email_subscr');
  if (email_subscr.value.trim() == '') {
    $('upper_need_email_div').style.display = 'block';
    return false;
  }
  $('notify_person').value = 'yes';
  return true;
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

//validate email if person subscribes to notifications
function validate_email() {
  var is_receive_updates = $('is_receive_updates');
  var auth_email = $('author_email');
  if (is_receive_updates.checked == true) {
  	if (auth_email.value.trim() == '') {
      $('need_email_div').style.display = 'block';
      $('author_email_original').style.color = '#ff0000';
      return false;    
    }
  }
  return true;
}