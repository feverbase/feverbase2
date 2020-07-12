/**
 * @license
 * Copyright 2020 The Feverbase Authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

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
