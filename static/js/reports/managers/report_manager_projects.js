const user_id = JSON.parse(document.getElementById("user_id").textContent);
$.ajaxSetup({
  beforeSend: function (xhr, settings) {
    if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
      xhr.setRequestHeader("X-CSRFToken", getCookie("csrftoken"));
    }
  },
});

function csrfSafeMethod(method) {
  // These HTTP methods do not require CSRF protection
  return /^(GET|HEAD|OPTIONS|TRACE)$/.test(method);
}

function getCookie(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    var cookies = document.cookie.split(";");
    for (var i = 0; i < cookies.length; i++) {
      var cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

$(document).ready(function () {
  function handleFilterChange() {
    var month = $("#month-filter").val();
    var year = $("#year-filter").val();
    var project = $("#project-filter").val();
    var user = $("#user-filter").val();

    $.ajax({
      url: `/api/report/project/manager/${user_id}`,
      method: "GET",
      data: {
        month: month,
        year: year,
        project: project,
        user: user,
      },
      success: function (response) {
        updateTable(response.projects);
      },
      error: function (xhr, status, error) {
        console.error(xhr.responseText);
      },
    });
  }

  function updateTable(response) {
    console.log(response);
    var logs_table_body = $("#logs-table");
    logs_table_body.empty();

    // Populate table with activity logs
    response.forEach(function (log) {
      var row = $("<tr>").appendTo(logs_table_body);
      $("<td>").text(log.project).appendTo(row);
      $("<td>").text(log.department).appendTo(row);
      $("<td>").text(log.location).appendTo(row);
      $("<td>").text(log.worked_hours).appendTo(row);
    });
  }

  $("#month-filter, #year-filter, #project-filter, #user-filter").change(
    function () {
      handleFilterChange();
    }
  );

  handleFilterChange(); // Initial call to load data
});
