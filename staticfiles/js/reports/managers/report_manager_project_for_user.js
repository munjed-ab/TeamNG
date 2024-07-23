const user_id = JSON.parse(document.getElementById("user_id").textContent);
var users_count = JSON.parse(
  document.getElementById("users_count").textContent
);
var projects_count = JSON.parse(
  document.getElementById("projects_count").textContent
);

users_count = users_count + 1;
projects_count = projects_count + 1;

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

function capitalizeName(name) {
  return name.charAt(0).toUpperCase() + name.slice(1).toLowerCase();
}

$(document).ready(function () {
  function handleFilterChange() {
    var month = $("#month-filter").val();
    var year = $("#year-filter").val();
    var user = $("#user-filter").val();

    $.ajax({
      url: `/apis/report/project-for-user/manager/${user_id}`,
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
    let users = [];
    var row_head = $("<tr>").appendTo(header_table);
    $("<th>")
      .html(
        `<i id='expand' style='display: flex; justify-content: center;cursor:pointer;' class='fa fa-arrows-alt fa-4x' aria-hidden='true'></i>`
      )
      .appendTo(row_head);

    response.forEach((all) => {
      if (!users.includes(all.user.name)) {
        users.push(all.user.name);
        var col_head = $("<tr>").appendTo(logs_table_body);
        $("<th class='table-head-color'>")
          .text(capitalizeName(all.user.name))
          .appendTo(col_head);

        for (let i = 0; i < response.length; i++) {
          if (all.user.name == response[i].user.name) {
            $("<td>").text(response[i].hours_worked).appendTo(col_head);
          }
        }

        $("<td>")
          .text(`${parseFloat(all.user.total_hours).toFixed(2)}`)
          .appendTo(col_head);
        $("<td>")
          .text(`${parseFloat(all.user.percentage).toFixed(2)}%`)
          .appendTo(col_head);
      }
    });
    var col_pro_tot = $("<tr>").appendTo(logs_table_body);
    var col_pro_per = $("<tr>").appendTo(logs_table_body);
    $("<th class='table-head-color bg-primary'>")
      .text("Total hours")
      .appendTo(col_pro_tot);
    $("<th class='table-head-color bg-primary'>")
      .text("Percentage")
      .appendTo(col_pro_per);

    response.forEach((all) => {
      if (!projects.includes(all.project.name)) {
        projects.push(all.project.name);

        $("<th>").text(all.project.name).appendTo(row_head);
        $("<td>")
          .text(`${parseFloat(all.project.total_hours).toFixed(2)}`)
          .appendTo(col_pro_tot);
        $("<td>")
          .text(`${parseFloat(all.project.percentage).toFixed(2)}%`)
          .appendTo(col_pro_per);
      }
    });

    $("<th class='table-head-color bg-primary'>")
      .text("Total hours")
      .appendTo(row_head);
    $("<th class='table-head-color bg-primary'>")
      .text("Percentage")
      .appendTo(row_head);
  }

  $("#month-filter, #year-filter, #user-filter").change(function () {
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
      ws["!cols"] = Array(25).fill({ wpx: 80 });
      ws["!rows"] = [{ hpx: 30 }];
      let cells = "BCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
      for (let index = 2; index < users_count + 4; index++) {
        if (ws[`A${index}`]) {
          if (ws[`A${index}`].v == "Percentage") {
            cells.forEach((cell) => {
              if (ws[`${cell}${index}`]) {
                ws[`${cell}${index}`].z = "0.00%";
              }
            });
          }
        }
      }

      if (ws[`${cells[projects_count]}1`]) {
        if ((ws[`${cells[projects_count]}1`].v = "Percentage")) {
          for (let index = 2; index < users_count + 4; index++) {
            if (ws[`${cells[projects_count]}${index}`]) {
              ws[`${cells[projects_count]}${index}`].z = "0.00%";
            }
          }
        }
      }

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
        `project_for_user_report_in_${year}_${month}_of_${user}.xlsb`
      );
    });

  $("#tableModal .btn-close").click(function () {
    $("#tableModal").modal("hide");
  });
  $(document).on("click", "#expand", function () {
    $("#modal-head").html($("#head").html());

    $("#modal-logs-table").html($("#logs-table").html());
    $("#tableModal").modal("show");
  });

  handleFilterChange(); // Initial call to load data
});
