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

    $.ajax({
      url: `/api/report/expectedhours/user/${user_id}`,
      method: "GET",
      data: {
        month: month,
        year: year,
        project: project,
      },
      success: function (response) {
        updateTable(response);
      },
      error: function (xhr, status, error) {
        console.error(xhr.responseText);
      },
    });
  }

  function updateTable(response) {
    var head_date = $("#date-range");
    head_date.empty();
    head_date.html(
      `Interval From ${response.date_range.start} to ${response.date_range.end}`
    );
    console.log(response);
    var logs_table_body = $("#logs-table");
    logs_table_body.empty();

    // Populate table with activity logs
    response.projects.forEach((project) => {
      var row = $("<tr>").appendTo(logs_table_body);
      $("<td>").text(project.name).appendTo(row);
      $("<td>")
        .text(`${parseFloat(project.percentage).toFixed(2)}%`)
        .appendTo(row);
    });

    var row1 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "RGB(99, 136, 199)", color: "white" });
    $("<td>").text("expected hours").appendTo(row1);
    $("<td>")
      .text(parseFloat(response.all.expected_hours).toFixed(2))
      .appendTo(row1);
    var row2 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "RGB(99, 136, 199)", color: "white" });
    $("<td>").text("worked hours").appendTo(row2);
    $("<td>")
      .text(parseFloat(response.all.total_worked_hours).toFixed(2))
      .appendTo(row2);
    var row3 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "RGB(99, 136, 199)", color: "white" });
    $("<td>").text("missed hours").appendTo(row3);
    $("<td>")
      .text(parseFloat(response.all.missed_hours).toFixed(2))
      .appendTo(row3);
    var row4 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "RGB(99, 136, 199)", color: "white" });
    $("<td>").text("public holiday hours").appendTo(row4);
    $("<td>")
      .text(parseFloat(response.all.hours_pub_holiday).toFixed(2))
      .appendTo(row4);
    var row5 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "RGB(99, 136, 199)", color: "white" });
    $("<td>").text("leave days hours").appendTo(row5);
    $("<td>")
      .text(parseFloat(response.all.hours_leave_days).toFixed(2))
      .appendTo(row5);
    var row6 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "RGB(99, 136, 199)", color: "white" });
    $("<td>").text("percent complete").appendTo(row6);
    $("<td>")
      .text(`${parseFloat(response.all.percent_complete).toFixed(2)}%`)
      .appendTo(row6);

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
