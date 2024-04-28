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
    var user = $("#user-filter").val();

    $.ajax({
      url: `/api/report/project-for-activity/manager/${user_id}`,
      method: "GET",
      data: {
        month: month,
        year: year,
        user: user,
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

      // Package and Release Data (`writeFile` tries to write and save an XLSB file)
      XLSX.writeFile(wb, "Report.xlsb");
    });
  handleFilterChange(); // Initial call to load data
});
