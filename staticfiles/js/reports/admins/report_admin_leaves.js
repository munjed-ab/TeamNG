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
    var user = $("#user-filter").val();
    var department = $("#department-filter").val();

    $.ajax({
      url: `/apis/report/leave/admin/${user_id}`,
      method: "GET",
      data: {
        month: month,
        year: year,
        user: user,
        department: department,
      },
      success: function (response) {
        updateTable(response.leaves);
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
      $("<td style='text-align: center;' colspan='12'>")
        .text("No Data")
        .appendTo(row);
      return;
    }
    const options = {
      day: "numeric",
      month: "short",
      year: "numeric",
    };
    // Populate table with activity logs
    response.forEach(function (log) {
      var row = $("<tr>").appendTo(logs_table_body);
      $("<td>").text(log.from).appendTo(row);
      $("<td>").text(log.to).appendTo(row);
      $("<td>").text(log.department).appendTo(row);
      $("<td>").text(log.location).appendTo(row);

      $("<td>").text(log.start_date).appendTo(row);
      $("<td>").text(log.end_date).appendTo(row);

      $("<td>").text(log.total_leave_days).appendTo(row);
      $("<td>").text(log.weekends_count).appendTo(row);
      $("<td>").text(log.pub_holidays_count).appendTo(row);
      $("<td>").text(log.actual_leave_days).appendTo(row);
      $("<td>").text(log.type).appendTo(row);
      $("<td>").text(log.respond).appendTo(row);
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

      var ws = wb.Sheets["Sheet1"];
      XLSX.utils.sheet_add_aoa(ws, [["Created " + new Date().toISOString()]], {
        origin: -1,
      });
      const range = XLSX.utils.decode_range(ws["!ref"]);

      // Calculate the number of rows
      const totalRows = range.e.r - range.s.r + 1;
      for (let index = 2; index < totalRows + 2; index++) {
        if (ws[`E${index}`]) {
          ws[`E${index}`].z = "d-mmm-yyyy";
          ws[`E${index}`].t = "d";
        }
        if (ws[`F${index}`]) {
          ws[`F${index}`].z = "d-mmm-yyyy";
          ws[`F${index}`].t = "d";
        }
        if (ws[`G${index}`]) {
          ws[`G${index}`].z = "#,##0";
          ws[`G${index}`].t = "n";
        }
        if (ws[`H${index}`]) {
          ws[`H${index}`].z = "#,##0";
          ws[`H${index}`].t = "n";
        }
        if (ws[`I${index}`]) {
          ws[`I${index}`].z = "#,##0";
          ws[`I${index}`].t = "n";
        }
        if (ws[`J${index}`]) {
          ws[`J${index}`].z = "#,##0";
          ws[`J${index}`].t = "n";
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
      XLSX.writeFile(
        wb,
        `leaves_report_in_${year}_${month}_of_${user}_${dept}.xlsx`
      );
    });
  handleFilterChange();
});
