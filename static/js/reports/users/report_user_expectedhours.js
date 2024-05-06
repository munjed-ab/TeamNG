const user_id = JSON.parse(document.getElementById("user_id").textContent);
const projects_count = JSON.parse(
  document.getElementById("projects_count").textContent
);
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

    $.ajax({
      url: `/apis/report/expectedhours/user/${user_id}`,
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
      .css({ "background-color": "var(--success)", color: "white" });
    $("<td>").text("worked hours").appendTo(row2);
    $("<td>")
      .text(parseFloat(response.all.total_worked_hours).toFixed(2))
      .appendTo(row2);
    var row3 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "var(--danger)", color: "white" });
    $("<td>").text("missed hours").appendTo(row3);
    $("<td>")
      .text(parseFloat(response.all.missed_hours).toFixed(2))
      .appendTo(row3);
    var row4 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "var(--blue)", color: "white" });
    $("<td>").text("public holiday hours").appendTo(row4);
    $("<td>")
      .text(parseFloat(response.all.hours_pub_holiday).toFixed(2))
      .appendTo(row4);
    var row5 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "var(--dark)", color: "white" });
    $("<td>").text("leave days hours").appendTo(row5);
    $("<td>")
      .text(parseFloat(response.all.hours_leave_days).toFixed(2))
      .appendTo(row5);
    var row6 = $("<tr>")
      .appendTo(logs_table_body)
      .css({ "background-color": "var(--info)", color: "white" });
    $("<td>").text("percent complete").appendTo(row6);
    $("<td>")
      .text(`${parseFloat(response.all.percent_complete).toFixed(2)}%`)
      .appendTo(row6);
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
      var project = $("#project-filter").val();
      if (project == "all") {
        for (let i = 2; i < projects_count + 3; i++) {
          if (ws[`B${i}`]) {
            ws[`B${i}`].z = "0.00%";
          }
        }
        if (ws[`B${projects_count + 1 + 1 + 6}`]) {
          ws[`B${projects_count + 1 + 1 + 6}`].z = "0.00%";
        } // 1 (header cell) + 1 (Leave cell) + 6 (static info cells) = (percent complete cell)
      } else {
        if (ws["B2"] && ws["B3"] && ws[`B${1 + 1 + 1 + 6}`]) {
          ws["B2"].z = "0.00%";
          ws["B3"].z = "0.00%";
          ws[`B${1 + 1 + 1 + 6}`].z = "0.00%"; //1 (one project) + 1 (header cell) + 1 (Leave cell) + 6 (static info cells) = (percent complete cell)
        }
      }

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
      XLSX.writeFile(
        wb,
        `expected_hours_report_in_${year}_${month}_of_${pro}.xlsb`
      );
    });
  handleFilterChange(); // Initial call to load data
});
