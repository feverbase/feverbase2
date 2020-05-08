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
var page = window.location.pathname === "/" ? -1 : 0;
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
            )} &middot; ${p.sponsor}</div>`
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
});

function toggleAdvancedFilters() {
  var status = $("#filters-status");
  var container = $("#filters-container");

  if (container.css("display") === "none") {
    container.css("display", "grid");
    status.html("Hide");
  } else {
    container.css("display", "none");
    status.html("");
  }
}
