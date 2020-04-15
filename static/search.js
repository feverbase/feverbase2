var page = 0;
var loadingTimeout = null;

function addPapers() {
  if (loadingTimeout || page === -1) {
    return;
  }

  var root = $("#rtable");

  var xhr = $.ajax({
    type: 'GET',
    dataType: 'json',
    contentType: 'application/json',
    data: { page: page + 1 },
    success: function (data) {
      console.log(data);
      clearTimeout(loadingTimeout);
      loadingTimeout = null;
      page = data.page;

      if (page === -1) {
        $('#noresults').show();
      }

      Array.from(data.papers).forEach(function (p) {
        var div = root.append('<div class="apaper"></div>');

        var tdiv = div.append('<div class="paperdesc"></div>');
        if (p.timestamp) {
          const timestamp = moment(p.timestamp.$date);
          tdiv.append(`<div class="ds">${timestamp.format('LL')} &middot; ${p.sponsor}</div>`);
        } else {
          tdiv.append(`<div class="ds">${p.sponsor}</div>`);
        }

        tdiv.append(`<div class="ts"><a href="${p.url}" target="_blank">${p.title}</a></div>`);

        const keys = ['title', 'url', 'timestamp', 'recruiting_status', 'sex', 'target_disease', 'intervention', 'sponsor', 'summary', 'location', 'institution', 'contact', 'sample_size', 'abandoned', 'abandoned_reason']
        for (var key of keys) {
          if (p[key] == undefined || p[key].length == 0) p[key] = 'Unspecified'
        }

        tdiv.append(`
          <blockquote class="as">
            <b>Condition</b>: ${p.target_disease}<br />
            <b>Intervention</b>: ${p.intervention}<br />
            <b>Sample Size</b>: ${p.sample_size}<br />
            <b>Location</b>: ${p.location}<br />
            <b>Status</b>: ${p.recruiting_status}
          </blockquote>
        `);
        tdiv.append('<br/>');
      });
    },
    error: function (jqXHR, textStatus, errorThrown) {
      console.log(jqXHR, textStatus, errorThrown);
      clearTimeout(loadingTimeout);
      loadingTimeout = null;
      page = -1;
      $('#noresults > :first-child').html('Refresh the page to try again.');
      $('#noresults').show();
      if (errorThrown !== 'abort') {
        toastr.error(errorThrown);
      }
    }
  });

  loadingTimeout = setTimeout(function () {
    toastr.error('Sorry! Request timed out.');
    xhr.abort();
  }, 60000);
}

$.ajaxSetup({
  beforeSend: function () {
    $("#loader").show();
  },
  complete: function () {
    $("#loader").hide();
  }
});

// toastr.options.positionClass = 'toast-bottom-right';

// when page loads...
$(document).ready(function () {

  // add papers to #rtable
  addPapers();

  // set up infinite scrolling for adding more papers
  $(window).on('scroll', function () {
    var scrollTop = $(document).scrollTop();
    var windowHeight = $(window).height();
    var bodyHeight = $(document).height() - windowHeight;
    var scrollPercentage = (scrollTop / bodyHeight);
    if (scrollPercentage > 0.9) {
      addPapers();
    }
  });
});

function toggleAdvancedFilters() {
  var status = document.getElementById('filters-status');
  var container = document.getElementById('filters-container');

  if (container.style.display === 'none') {
    container.style.display = 'grid';
    status.innerHTML = 'Hide';
  } else {
    container.style.display = 'none';
    status.innerHTML = '';
  }
}
