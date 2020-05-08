"use strict";

// when page loads...
$(document).ready(function () {
  // handle adding/deleting other symptoms
  // delete other if unchecking checkbox
  $("form").on(
    "change",
    'label.check.other > input[type="checkbox"]',
    function () {
      var value = parseInt(this.value);
      // if unchecked and not last other, try to delete
      if (!this.checked && value < $("label.check.other").length - 1) {
        deleteOther(value);
      }
    }
  );
  // dont unfocus text field if checkbox clicked
  $("form").on(
    "mousedown",
    'label.check.other > input[type="checkbox"]',
    function (e) {
      e.preventDefault();
    }
  );
  // typing in text box
  // entered key
  $("form").on("keyup", 'label.check.other > input[type="text"]', function () {
    var elem = $(this);
    var label = elem.parent();
    var checkbox = elem.siblings('input[type="checkbox"]');
    var value = parseInt(checkbox.attr("value"));
    var labelCount = $("label.check.other").length;

    // check if element input empty
    if ((elem.val() || "").length === 0) {
      // only delete next if is second to last
      if (value === labelCount - 2) {
        // delete next
        label.next("label.check.other").remove();
        // reset so can add new other again
        elem.data("added", false);
      }

      // uncheck current other
      checkbox.prop("checked", false);
    } else {
      // if has not added yet, add new other
      // only add new one if is last
      if (!elem.data("added") && value == labelCount - 1) {
        // add new other to DOM
        var newOther = label.clone();
        // clear data and set new value
        newOther
          .find('input[type="checkbox"]')
          .attr("value", value + 1)
          .prop("checked", false);
        newOther.find('input[type="text"]').val("");
        // add
        label.after(newOther);
        // dont add again until deleted
        elem.data("added", true);
      }

      // check current other
      checkbox.prop("checked", true);
    }
  });
});

function deleteOther(num) {
  // if only one left, don't delete
  if ($("label.check.other").length < 2) {
    return;
  }

  // get currently focused element to refocus after shuffle
  var focused = $(document.activeElement);

  // remove
  $(
    'label.check.other:has(input[type="checkbox"][value="' + num + '"])'
  ).remove();

  // get initial insertion point
  var lastCorrectLabel = $("label.check:not(.other)").last();
  // shuffle
  $("label.check.other").each(function (idx) {
    var elem = $(this);
    // change value
    elem.find('input[type="checkbox"]').attr("value", idx);
    // move to correct spot
    lastCorrectLabel.after(elem);
    lastCorrectLabel = elem;
  });

  // refocus element
  if (focused) {
    focused.focus();
  }
}
