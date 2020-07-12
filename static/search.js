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

// setup

$.ajaxSetup({
  beforeSend: function () {
    $("#loader").show();
  },
  complete: function () {
    $("#loader").hide();
  },
});

// toastr.options.positionClass = 'toast-bottom-right';

// if not on search, dont add
var page = 0;
var loadingTimeout = null;

function addPapers() {
  if (loadingTimeout || page === -1) {
    return;
  }

  var root = $("#rtable");

  var xhr = $.ajax({
    type: "GET",
    dataType: "json",
    contentType: "application/json",
    data: { page: page + 1 },
    success: function (data) {
      console.log(data);
      clearTimeout(loadingTimeout);
      loadingTimeout = null;
      page = data.page;

      if (data.alerts && data.alerts.length) {
        for (const m of data.alerts) {
          if ("type" in m && "message" in m) {
            toastr[m.type](m.message);
          }
        }
      }

      if (!data.papers || !data.papers.length) {
        $("#noresults").show();
        page = -1;
        return;
      }

      if (page === -1) {
        $("#noresults").show();
      }

      if (data.stats) {
        $("#stats").html(data.stats).show();
      } else {
        $("#stats").html("").hide();
      }

      for (const p of data.papers) {
        var div = root.append("<div></div>");

        var tdiv = div.append("<div></div>");
        if (p.timestamp && p.timestamp !== -1) {
          const timestamp = moment.utc(p.timestamp);
          tdiv.append(
            `<div class="pretitle-container">${timestamp.format(
              "LL"
            )} &middot; ${p.sponsor} &middot; ${getRegistry(p.url)}</div>`
          );
        } else {
          tdiv.append(`<div class="pretitle-container">${p.sponsor}</div>`);
        }

        tdiv.append(
          `<div class="title-container"><a href="${p.url}" target="_blank">${p.title}</a></div>`
        );

        const keys = [
          "title",
          "url",
          "timestamp",
          "recruiting_status",
          "sex",
          "target_disease",
          "intervention",
          "sponsor",
          "summary",
          "location",
          "institution",
          "contact",
          "sample_size",
          "abandoned",
          "abandoned_reason",
        ];
        for (var key of keys) {
          if (p[key] == undefined || p[key].length == 0) p[key] = "Unspecified";
        }

        tdiv.append(`
          <blockquote>
            <b>Condition</b>: ${p.target_disease}<br />
            <b>Intervention</b>: ${p.intervention}<br />
            <b>Sample Size</b>: ${p.sample_size}<br />
            <b>Location</b>: ${p.location}<br />
            <b>Status</b>: ${p.recruiting_status}<br />
            <b>Summary</b>: ${p.summary}
          </blockquote>
        `);
        tdiv.append("<br/>");
      }
    },
    error: function (jqXHR, textStatus, errorThrown) {
      console.log(jqXHR, textStatus, errorThrown);
      clearTimeout(loadingTimeout);
      loadingTimeout = null;
      page = -1;
      $("#noresults > :first-child").html("Refresh the page to try again.");
      $("#noresults").show();
      if (errorThrown !== "abort") {
        toastr.error(
          "An unexpected error occurred. Please either try a different search query or try again later."
        );
      }
    },
  });

  loadingTimeout = setTimeout(function () {
    toastr.error("Sorry! Request timed out.");
    xhr.abort();
  }, 60000);
}

// when page loads...
$(document).ready(function () {
  // splash search page, no results
  if (window.location.pathname === "/") {
    var q = $("#qfield");
    $(".shortcut-filter").click(function () {
      var text = $(this).data("text");
      var idxFromEnd = text.length - text.indexOf("|");
      text = text.replace("|", "");

      var newVal = (q.val().trim() + " " + text).trim();
      q.val(newVal);
      q.focus();

      var idx = newVal.length - idxFromEnd + 1;
      q[0].setSelectionRange(idx, idx);
    });

    // search page after results returned
  } else {
    // add papers to #rtable
    addPapers();

    // set up infinite scrolling for adding more papers
    $(window).on("scroll", function () {
      var scrollTop = $(document).scrollTop();
      var windowHeight = $(window).height();
      var bodyHeight = $(document).height() - windowHeight;
      var scrollPercentage = scrollTop / bodyHeight;
      if (scrollPercentage > 0.9) {
        addPapers();
      }
    });
  }
});

function toggleAdvancedFilters() {
  var status = $("#filters-status");
  var container = $("#filters-container");
  var reset = $("#filters-reset");

  if (container.css("display") === "none") {
    container.css("display", "grid");
    status.html("Hide");
    reset.html("Reset Advanced Filters")
  } else {
    container.css("display", "none");
    status.html("");
    reset.html("");
  }
}

function resetAdvancedFilters() {
  $("#filter-min-timestamp").val("");
  $("#filter-max-timestamp").val("");
  $("#filter-min-sample_size").val("");
  $("#filter-max-sample_size").val("");
  $("#filter-location").val("");
  $("#filter-sponsor").val("");
  $("#filter-target_disease").val("");
  $("#filter-intervention").val("");
  $("#filter-recruiting_status").val("");
}
  
// TODO(gmittal): Move this to server-side
function getRegistry(url) {
  let host = url.split("/")[2];
  let registries = {
    "clinicaltrials.gov": "clinicaltrials.gov",
    "www.clinicaltrialsregister.eu": "EU Clinical Trials Register",
    "isrctn.com": "ISRCTN",
  };
  return registries[host];
}
