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

    $.ajax({
      url: `/apis/report/missed_hours/manager/${user_id}`,
      method: "GET",
      data: {
        month: month,
        year: year,
        user: user,
      },
      success: function (response) {
        updateTable(response.users);
      },
      error: function (xhr, status, error) {
        console.error(xhr.responseText);
      },
    });
  }

  function updateTable(response) {
    var logs_table_body = $("#logs-table");
    logs_table_body.empty();

    // Populate table with activity logs
    response.forEach(function (log) {
      var row = $("<tr>").appendTo(logs_table_body);
      $("<td>").text(log.name).appendTo(row);
      $("<td>").text(log.role).appendTo(row);
      $("<td>").text(log.department).appendTo(row);
      $("<td>").text(log.location).appendTo(row);
      $("<td>")
        .css({ "background-color": "var(--success)", color: "white" })
        .text(
          new Intl.NumberFormat().format(
            parseFloat(log.expected_hours).toFixed(2)
          )
        )
        .appendTo(row);
      $("<td>")
        .css({ "background-color": "var(--info)", color: "white" })
        .text(
          new Intl.NumberFormat().format(
            parseFloat(log.worked_hours).toFixed(2)
          )
        )
        .appendTo(row);
      $("<td>")
        .css({ "background-color": "var(--dark)", color: "white" })
        .text(
          new Intl.NumberFormat().format(parseFloat(log.leave_hours).toFixed(2))
        )
        .appendTo(row);
      $("<td>")
        .css({ "background-color": "var(--danger)", color: "white" })
        .text(
          new Intl.NumberFormat().format(
            parseFloat(log.missed_hours).toFixed(2)
          )
        )
        .appendTo(row);
    });
  }

  $(
    "#month-filter, #year-filter, #user-filter, #department-filter, #project-filter"
  ).change(function () {
    var selectedFilter = $(this).attr("id");

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
          ws[`E${index}`].z = "#,##0.00";
          ws[`E${index}`].t = "n";
        }
        if (ws[`F${index}`]) {
          ws[`F${index}`].z = "#,##0.00";
          ws[`F${index}`].t = "n";
        }
        if (ws[`G${index}`]) {
          ws[`G${index}`].z = "#,##0.00";
          ws[`G${index}`].t = "n";
        }
        if (ws[`H${index}`]) {
          ws[`H${index}`].z = "#,##0.00";
          ws[`H${index}`].t = "n";
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

      if (user == "all") {
        user = "all";
      } else {
        user = $("#user-filter option:selected").text();
      }
      XLSX.writeFile(
        wb,
        `missed_hours_report_in_${year}_${month}_of_${user}.xlsx`
      );
    });
  handleFilterChange(); // Initial call to load data
});
