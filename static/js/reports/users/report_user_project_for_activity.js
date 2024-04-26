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

    $.ajax({
      url: `/api/report/project-for-activity/user/${user_id}`,
      method: "GET",
      data: {
        month: month,
        year: year,
      },
      success: function (response) {
        updateTable(response.report);
      },
      error: function (xhr, status, error) {
        console.error(xhr.responseText);
      },
    });
  }

  function updateTable(response) {
    var logs_table_body = $("#logs-table");
    logs_table_body.empty();
    var header_table = $("#head");
    header_table.empty();
    // TODO: render the table
    // Create table headers

    // Populate table with activity logs
    let projects = [];
    let activitys = [];
    var row_head = $("<tr>").appendTo(header_table);
    $("<th>").text("").appendTo(row_head);

    response.forEach((all) => {
      if (!activitys.includes(all.activity.name)) {
        activitys.push(all.activity.name);
        var col_head = $("<tr>").appendTo(logs_table_body);
        $("<th class='table-head-color'>")
          .text(all.activity.name)
          .appendTo(col_head);

        for (let i = 0; i < response.length; i++) {
          if (all.activity.name == response[i].activity.name) {
            $("<td>").text(response[i].hours_worked).appendTo(col_head);
          }
        }

        $("<td>")
          .text(`${parseFloat(all.activity.percentage).toFixed(2)}%`)
          .appendTo(col_head);
      }
    });

    var col_pro_per = $("<tr>").appendTo(logs_table_body);
    $("<th class='table-head-color'>").text("Percentage").appendTo(col_pro_per);
    response.forEach((all) => {
      if (!projects.includes(all.project.name)) {
        projects.push(all.project.name);

        $("<th>").text(all.project.name).appendTo(row_head);
        $("<td>")
          .text(`${parseFloat(all.project.percentage).toFixed(2)}%`)
          .appendTo(col_pro_per);
      }
    });

    $("<th>").text("Percentage").appendTo(row_head);
    for (let i = 0; i < response.length; i++) {
      if (all.activity.name == response[i].activity.name) {
        $("<td>").text(response[i].hours_worked).appendTo(col_head);
      }
    }
    // var row1 = $("<tr>")
    //   .appendTo(logs_table_body)
    //   .css({ "background-color": "RGB(99, 136, 199)", color: "white" });
    // $("<td>").text("expected hours").appendTo(row1);
    // $("<td>")
    //   .text(parseFloat(response.all.expected_hours).toFixed(2))
    //   .appendTo(row1);
    // var row2 = $("<tr>")
    //   .appendTo(logs_table_body)
    //   .css({ "background-color": "RGB(99, 136, 199)", color: "white" });
    // $("<td>").text("worked hours").appendTo(row2);
    // $("<td>")
    //   .text(parseFloat(response.all.total_worked_hours).toFixed(2))
    //   .appendTo(row2);
    // var row3 = $("<tr>")
    //   .appendTo(logs_table_body)
    //   .css({ "background-color": "RGB(99, 136, 199)", color: "white" });
    // $("<td>").text("missed hours").appendTo(row3);
    // $("<td>")
    //   .text(parseFloat(response.all.missed_hours).toFixed(2))
    //   .appendTo(row3);
    // var row4 = $("<tr>")
    //   .appendTo(logs_table_body)
    //   .css({ "background-color": "RGB(99, 136, 199)", color: "white" });
    // $("<td>").text("public holiday hours").appendTo(row4);
    // $("<td>")
    //   .text(parseFloat(response.all.hours_pub_holiday).toFixed(2))
    //   .appendTo(row4);
    // var row5 = $("<tr>")
    //   .appendTo(logs_table_body)
    //   .css({ "background-color": "RGB(99, 136, 199)", color: "white" });
    // $("<td>").text("leave days hours").appendTo(row5);
    // $("<td>")
    //   .text(parseFloat(response.all.hours_leave_days).toFixed(2))
    //   .appendTo(row5);
    // var row6 = $("<tr>")
    //   .appendTo(logs_table_body)
    //   .css({ "background-color": "RGB(99, 136, 199)", color: "white" });
    // $("<td>").text("percent complete").appendTo(row6);
    // $("<td>")
    //   .text(`${parseFloat(response.all.percent_complete).toFixed(2)}%`)
    //   .appendTo(row6);
  }

  $("#month-filter, #year-filter, #project-filter").change(function () {
    handleFilterChange();
  });

  handleFilterChange(); // Initial call to load data
});
