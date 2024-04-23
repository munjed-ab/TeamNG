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
    var user = user_id;
    var project = $("#project-filter").val();

    $.ajax({
      url: `/api/report/user/${user_id}`,
      method: "GET",
      data: {
        month: month,
        year: year,
        project: project,
      },
      success: function (response) {
        updateProjectCards(response.activity_logs);
      },
      error: function (xhr, status, error) {
        console.error(xhr.responseText);
      },
    });
  }

  function updateProjectCards(response) {
    console.log(response);
    var logs_table_body = $("#logs-table");
    logs_table_body.empty();

    // Populate table with activity logs
    response.forEach(function (log) {
      var row = $("<tr>").appendTo(logs_table_body);
      $("<td>").text(log.time_added).appendTo(row);
      $("<td>").text(log.username).appendTo(row);
      $("<td>").text(log.project).appendTo(row);

      $("<td>").text(log.activity).appendTo(row);
      $("<td>").text(log.department).appendTo(row);
      $("<td>").text(log.date).appendTo(row);
      $("<td>").text(parseFloat(log.hours_worked).toFixed(2)).appendTo(row);
      $("<td>").text(log.details).appendTo(row);
    });

    // // Attach downloadExcel function to the download button click event
    // $("#downloadExcelBtn").click(function () {
    //   downloadExcel(activityLogs, name);
    // });

    // $("#activityLogsModal").modal("show");
  }

  $("#month-filter, #year-filter, #project-filter").change(function () {
    handleFilterChange();
  });

  handleFilterChange(); // Initial call to load data
});
