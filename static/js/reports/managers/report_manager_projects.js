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

    $.ajax({
      url: `/apis/report/project/manager/${user_id}`,
      method: "GET",
      data: {
        month: month,
        year: year,
        project: project,
        user: user,
      },
      success: function (response) {
        updateTable(response.projects);
      },
      error: function (xhr, status, error) {
        console.error(xhr.responseText);
      },
    });
  }

  function updateTable(response) {
    console.log(response);
    var logs_table_body = $("#logs-table");
    logs_table_body.empty();

    // Populate table with activity logs
    response.forEach(function (log) {
      var row = $("<tr>").appendTo(logs_table_body);
      $("<td>").text(log.project).appendTo(row);
      $("<td>").text(log.department).appendTo(row);
      $("<td>").text(log.location).appendTo(row);
      $("<td>")
        .text(
          new Intl.NumberFormat().format(
            parseFloat(log.worked_hours).toFixed(2)
          )
        )
        .appendTo(row);
    });
  }

  $("#month-filter, #year-filter, #project-filter, #user-filter").change(
    function () {
      handleFilterChange();
    }
  );
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
      var month = $("#month-filter").val();
      var year = $("#year-filter").val();
      if (month == "all") {
        month = "_";
      }
      var user = $("#user-filter").val();
      var pro = $("#project-filter").val();

      if (user == "all") {
        user = "all";
      } else {
        user = $("#user-filter option:selected").text();
      }
      if (pro == "all") {
        pro = "_";
      } else {
        pro = $("#department-filter option:selected").text();
      }
      XLSX.writeFile(
        wb,
        `projects_report_in_${year}_${month}_of_${user}_${pro}.xlsb`
      );
    });
  handleFilterChange(); // Initial call to load data
});
