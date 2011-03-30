var caret_index = 1;

function $(id) {
  return document.getElementById(id);
}

function row_color(index) {
  var accept = $('item-' + index + '-accept').checked;
  var flag = $('item-' + index + '-flag').checked;
  var current = index == caret_index;
  return accept ? '#dfd' : flag ? '#fdd' : current ? '#ffd' : '#fff';
}

function move_caret(new_index) {
  var old_index = caret_index;
  var row = $('caret-' + new_index);
  if (row) {
    caret_index = new_index;
    update_row(old_index);
    update_row(new_index);
    scroll_into_view(row);
  }
}

function scroll_into_view(element) {
  var viewport_top = (document.body.scrollTop +
                      document.documentElement.scrollTop);
  var viewport_height = window.innerHeight;
  var element_box = element.getBoundingClientRect();
  var pixels_to_overlap = element_box.bottom - element_box.top + 8;

  var scroll_to;
  if (element_box.top < 0) {
    scroll_to = viewport_top +
                pixels_to_overlap + element_box.bottom - viewport_height;
  } else if (element_box.bottom > viewport_height) {
    scroll_to = viewport_top + element_box.top - pixels_to_overlap;
  } else {
    return;
  }

  scroll_to = Math.min(document.body.scrollHeight - viewport_height,
                       Math.max(0, scroll_to));
  window.scroll(document.body.scrollLeft +
                document.documentElement.scrollLeft,
                scroll_to);
}

function update_row(index) {
  $('caret-' + index).innerHTML = (index == caret_index) ? '\u25b6' : '';
  $('item-' + index).style.backgroundColor = row_color(index);
}

function keydown(event) {
  var accept = $('item-' + caret_index + '-accept');
  var flag = $('item-' + caret_index + '-flag');

  switch (event.keyCode) {
    case 74:  // j
      move_caret(caret_index + 1);
      break;
    case 75:  // k
      move_caret(caret_index - 1);
      break;
    case 65:  // a
      accept.checked = !accept.checked;
      if (accept.checked) flag.checked = false;
      move_caret(caret_index + 1);
      break;
    case 70:  // f
      flag.checked = !flag.checked;
      if (flag.checked) accept.checked = false;
      move_caret(caret_index + 1);
      break;
    case 79:  // o
      window.open($('link-' + caret_index).href, '_blank');
      break;
    case 13:  // Enter
      $('review-form').submit();
      break;
  }
}

function init() {
  move_caret(1);
  document.onkeydown = keydown;
}
