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
    var department = $("#department-filter").val();

    $.ajax({
      url: `/api/report/expected_hours/admin/${user_id}`,
      method: "GET",
      data: {
        month: month,
        year: year,
        project: project,
        user: user,
        department: department,
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
      .text(
        new Intl.NumberFormat().format(
          parseFloat(response.all.expected_hours).toFixed(2)
        )
      )
      .appendTo(row1);
    var row2 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "var(--success)", color: "white" });
    $("<td>").text("worked hours").appendTo(row2);
    $("<td>")
      .text(
        new Intl.NumberFormat().format(
          parseFloat(response.all.total_worked_hours).toFixed(2)
        )
      )
      .appendTo(row2);
    var row3 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "var(--danger)", color: "white" });
    $("<td>").text("missed hours").appendTo(row3);
    $("<td>")
      .text(
        new Intl.NumberFormat().format(
          parseFloat(response.all.missed_hours).toFixed(2)
        )
      )
      .appendTo(row3);
    var row4 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "var(--blue)", color: "white" });
    $("<td>").text("public holiday hours").appendTo(row4);
    $("<td>")
      .text(
        new Intl.NumberFormat().format(
          parseFloat(response.all.hours_pub_holiday).toFixed(2)
        )
      )
      .appendTo(row4);
    var row5 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "var(--dark)", color: "white" });
    $("<td>").text("leave days hours").appendTo(row5);
    $("<td>")
      .text(
        new Intl.NumberFormat().format(
          parseFloat(response.all.hours_leave_days).toFixed(2)
        )
      )
      .appendTo(row5);
    var row6 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "var(--info)", color: "white" });
    $("<td>").text("percent complete").appendTo(row6);
    $("<td>")
      .text(`${parseFloat(response.all.percent_complete).toFixed(2)}%`)
      .appendTo(row6);
  }

  $(
    "#month-filter, #year-filter, #user-filter, #department-filter, #project-filter"
  ).change(function () {
    var selectedFilter = $(this).attr("id");

    if (selectedFilter === "user-filter") {
      // Reset department filter to "all"
      $("#department-filter").val("all");
    } else if (selectedFilter === "department-filter") {
      // Reset user filter to "all"
      $("#user-filter").val("all");
    }
    handleFilterChange();
  });
  document
    .getElementById("downloadExcelBtn")
    .addEventListener("click", function () {
      /* Create worksheet from HTML DOM TABLE */
      var wb = XLSX.utils.table_to_book(
        document.getElementById("TableToExport")
      );

      // Process Data (add a new row)
      var ws = wb.Sheets["Sheet1"];
      XLSX.utils.sheet_add_aoa(ws, [["Created " + new Date().toISOString()]], {
        origin: -1,
      });
      ws["B4"].z = "0.00%";
      // Package and Release Data (`writeFile` tries to write and save an XLSB file)
      XLSX.writeFile(wb, "Report.xlsb");
    });
  handleFilterChange(); // Initial call to load data
});
