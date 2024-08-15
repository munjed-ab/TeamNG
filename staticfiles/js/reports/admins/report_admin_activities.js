const user_id = JSON.parse(document.getElementById("user_id").textContent);
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
      url: `/apis/report/activity/admin/${user_id}`,
      method: "GET",
      data: {
        month: month,
        year: year,
        project: project,
        user: user,
        department: department,
      },
      success: function (response) {
        updateTable(response.activity_logs);
      },
      error: function (xhr, status, error) {
        console.error(xhr.responseText);
      },
    });
  }
  const options = {
    dateStyle: "medium",
    day: "numeric",
    month: "short",
    year: "numeric",
  };
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
      $("<td>").text(log.date).appendTo(row);
      $("<td>").text(parseFloat(log.hours_worked).toFixed(2)).appendTo(row);
      $("<td>").text(log.details).appendTo(row);
    });
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
      //TODO: solve the hell out of this task already!!!!
      // Get the range of the sheet
      const range = XLSX.utils.decode_range(ws["!ref"]);

      // Calculate the number of rows
      const totalRows = range.e.r - range.s.r + 1;
      for (let index = 2; index < totalRows + 2; index++) {
        if (ws[`H${index}`]) {
          ws[`H${index}`].z = "#,##0.00";
          ws[`H${index}`].t = "n";
        }
        if (ws[`G${index}`]) {
          ws[`G${index}`].z = "d-mmm-yyyy";
          ws[`G${index}`].t = "d";
        }
        if (ws[`A${index}`] && !isNaN(ws[`A${index}`])) {
          ws[`A${index}`].z = "d-mmm-yyyy [hh:mm:ss]";
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
      var user = $("#user-filter").val();
      var dept = $("#department-filter").val();
      var pro = $("#project-filter").val();

      if (user == "all") {
        user = "all";
        if (dept == "all") {
          dept = "_";
        } else {
          dept = $("#department-filter option:selected").text();
        }
      } else {
        user = $("#user-filter option:selected").text();
        dept = "_";
      }
      if (pro == "all") {
        pro = "_";
      } else {
        pro = $("#department-filter option:selected").text();
      }
      XLSX.writeFile(
        wb,
        `activities_report_in_${year}_${month}_of_${user}_${dept}_${pro}.xlsx`
      );
    });
  handleFilterChange(); // Initial call to load data
});
