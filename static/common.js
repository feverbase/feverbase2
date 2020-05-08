"use strict";

$(document).ready(function () {
  // prevent
  $("#feedback-box").click(function (e) {
    e.stopPropagation();
  });
});

function toggleFeedback() {
  var container = $("#feedback");

  if (container.css("display") === "none") {
    container.css("display", "flex");
  } else {
    container.css("display", "none");
  }
}

var submittingFeedback = false;
function submitFeedback() {
  if (submittingFeedback) {
    return;
  }
  submittingFeedback = true;
  var subject = $("#feedback-subject").val().trim();
  var body = $("#feedback-body").val().trim();
  var xhr = $.ajax("/feedback", {
    type: "GET",
    data: { subject, body },
    beforeSend: null, // dont show loader
    success: function (data) {
      toastr.success(data);

      $("#feedback-subject").val("");
      $("#feedback-body").val("");
      $("#feedback-container").css("display", "none");
      $("#feedback-status").html("");
    },
    error: function (jqXHR, textStatus, errorThrown) {
      console.log(jqXHR, textStatus, errorThrown);
      toastr.error(jqXHR.responseText);
    },
  }).always(function () {
    submittingFeedback = false;
  });
}
