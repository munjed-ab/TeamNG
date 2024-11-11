const user_id = JSON.parse(document.getElementById("user_id").textContent);
// Get the client's timezone offset in minutes
const clientTimezoneOffset = new Date().getTimezoneOffset() * 60000;
const currentDate = new Date();
const currentMonth = currentDate.getMonth() + 1; // Months are zero-indexed

var month = document.getElementById("month-filter");
var options = [...month.options];
options.forEach(function (option) {
  if (option.value == currentMonth) {
    option.selected = true;
  }
});
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
      url: `/apis/report/activity/user/${user_id}`,
      method: "GET",
      mode: "same-origin",
      data: {
        month: month,
        year: year,
        project: project,
      },
      success: function (response) {
        updateTable(response.activity_logs);
      },
      error: function (xhr, status, error) {
        console.error(xhr.responseText);
      },
    });
  }

  function updateTable(response) {
    var logs_table_body = $("#logs-table");
    logs_table_body.empty();
    if (response.length == 0) {
      var row = $("<tr>").appendTo(logs_table_body);
      $("<td style='text-align: center;' colspan='9'>")
        .text("No Data")
        .appendTo(row);
      return;
    }
    // Populate table with activity logs
    response.forEach(function (log) {
      var row = $("<tr>").appendTo(logs_table_body);
      $("<td>").text(log.time_added).appendTo(row);
      $("<td>").text(log.username).appendTo(row);
      $("<td>").text(log.project).appendTo(row);

      $("<td>").text(log.activity).appendTo(row);
      $("<td>").text(log.department).appendTo(row);
      $("<td>").text(log.location).appendTo(row);
      $("<td>")
        .text(
          new Date(
            new Date(log.date + "T00:00:00Z").getTime() - clientTimezoneOffset
          ).toDateString()
        )
        .appendTo(row);
      $("<td>").text(parseFloat(log.hours_worked).toFixed(2)).appendTo(row);
      $("<td>").text(log.details).appendTo(row);
    });
  }

  $("#month-filter, #year-filter, #project-filter").change(function () {
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

      const range = XLSX.utils.decode_range(ws["!ref"]);

      // Calculate the number of rows
      const totalRows = range.e.r - range.s.r + 1;
      for (let index = 2; index < totalRows + 2; index++) {
        if (ws[`H${index}`]) {
          ws[`H${index}`].z = "#,##0.00";
          ws[`H${index}`].t = "n";
        }
        if (ws[`G${index}`]) {
          const originalDate = new Date(ws[`G${index}`].v);
          const utcDate = new Date(
            originalDate.getTime() - clientTimezoneOffset
          );
          ws[`G${index}`].v = utcDate.toISOString().slice(0, 10);
          ws[`G${index}`].z = "d-mmm-yyyy";
          ws[`G${index}`].t = "d";
        }
        if (ws[`A${index}`] && !isNaN(ws[`A${index}`])) {
          const originalDate = new Date(ws[`A${index}`].v);
          const utcDate = new Date(
            originalDate.getTime() - clientTimezoneOffset
          );
          ws[`A${index}`].v = utcDate.toISOString().slice(0, 10);
          ws[`A${index}`].z = "d-mmm-yyyy";
          ws[`A${index}`].t = "d";
        }
      }
      ws["!cols"] = [
        { wpx: 80 },
        { wpx: 80 },
        { wpx: 80 },
        { wpx: 80 },
        { wpx: 80 },
        { wpx: 80 },
        { wpx: 80 },
        { wpx: 80 },
        { wpx: 80 },
        { wpx: 80 },
        { wpx: 80 },
      ];
      ws["!rows"] = [{ hpx: 30 }];
      var month = $("#month-filter").val();
      var year = $("#year-filter").val();
      if (month == "all") {
        month = "_";
      }

      var pro = $("#project-filter").val();

      if (pro == "all") {
        pro = "_";
      } else {
        pro = $("#department-filter option:selected").text();
      }
      XLSX.writeFile(wb, `activities_report_in_${year}_${month}_${pro}.xlsx`);
    });
  handleFilterChange(); // Initial call to load data
});
