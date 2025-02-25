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
      url: "/apis/report/holiday/",
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
    if (response.length == 0) {
      var row = $("<tr>").appendTo(logs_table_body);
      $("<td style='text-align: center;' colspan='2'>")
        .text("No Data")
        .appendTo(row);
      return;
    }
    // Populate table with activity logs
    response.forEach(function (log) {
      var row = $("<tr>").appendTo(logs_table_body);
      $("<td>").text(log.name).appendTo(row);
      $("<td>")
        .text(
          new Date(
            new Date(log.date + "T00:00:00Z").getTime() - clientTimezoneOffset
          ).toDateString()
        )
        .appendTo(row);
    });
  }

  $("#month-filter, #year-filter").change(function () {
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
        if (ws[`B${index}`]) {
          const originalDate = new Date(ws[`B${index}`].v);
          const utcDate = new Date(
            originalDate.getTime() - clientTimezoneOffset
          );
          ws[`B${index}`].v = utcDate.toISOString().slice(0, 10);
          ws[`B${index}`].z = "d-mmm-yyyy";
          ws[`B${index}`].t = "d";
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

      XLSX.writeFile(wb, `holidays_report_in_${year}_${month}.xlsx`);
    });
  handleFilterChange();
});
