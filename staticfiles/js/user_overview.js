const user_id = JSON.parse(document.getElementById("user_id").textContent);
const user_name = JSON.parse(document.getElementById("user_name").textContent);

const currentDate = new Date();
const currentMonth = currentDate.getMonth() + 1; // Months are zero-indexed

var month = document.getElementById("month-filter");
var options = [...month.options];
options.forEach(function (option) {
  if (option.value == currentMonth) {
    option.selected = true;
  }
});

function getProgressBarColor(percentage) {
  if (percentage >= 75) {
    return "bg-gradient-success";
  } else if (percentage >= 50) {
    return "bg-gradient-info";
  } else if (percentage >= 25) {
    return "bg-gradient-warning";
  } else {
    return "bg-gradient-danger";
  }
}
// overview.js
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
      url: `/apis/overview_user_data/${user_id}`,
      method: "GET",
      data: {
        month: month,
        year: year,
        project: project,
      },
      success: function (response) {
        updateProjectCards(response.projects);

        updateActivityCards(response.activities);

        updateStatisticsTable(response.all);
      },
      error: function (xhr, status, error) {
        console.error(xhr.responseText);
      },
    });
  }

  function updateProjectCards(projects) {
    var projectCardBody = $(".card-body-projects");
    projectCardBody.empty();
    projects.forEach(function (project) {
      var projectName = project.name;
      var percentage = parseFloat(project.percentage).toFixed(2);
      var progressBarColor = getProgressBarColor(percentage);

      var projectCard = `
        <div class="mb-4 project-card" data-project-name="${projectName}" data-activity-logs='${JSON.stringify(
        {
          name: projectName,
          activityLogs: project.activity_logs,
        }
      )}'>
            <h4 class="small font-weight-bold">${projectName} (${
        project.total
      } h)
                <span class="float-right">${percentage}%</span>
            </h4>
            <div class="progress">
                <div class="progress-bar ${progressBarColor}" role="progressbar" style="width: ${percentage}%" aria-valuenow="${percentage}" aria-valuemin="0" aria-valuemax="100"></div>
            </div>
        </div>
      `;
      projectCardBody.append(projectCard);
    });
  }

  function updateActivityCards(activities) {
    var activityCardBody = $(".card-body-activity");
    activityCardBody.empty();
    activities.forEach(function (activity) {
      var activityName = activity.name;
      var percentage = parseFloat(activity.percentage).toFixed(2);
      var progressBarColor = getProgressBarColor(percentage);

      var activityCard = `
        <div class="mb-4 activity-card" data-project-name="${activityName}" data-activity-logs='${JSON.stringify(
        {
          name: activityName,
          activityLogs: activity.activity_logs,
        }
      )}'>
            <h4 class="small font-weight-bold">${activityName} (${
        activity.total
      } h)
                <span class="float-right">${percentage}%</span>
            </h4>
            <div class="progress">
                <div class="progress-bar ${progressBarColor}" role="progressbar" style="width: ${percentage}%" aria-valuenow="${percentage}" aria-valuemin="0" aria-valuemax="100"></div>
            </div>
        </div>
      `;
      activityCardBody.append(activityCard);
    });
  }

  function updateStatisticsTable(allData) {
    $(".w-h").html(
      new Intl.NumberFormat().format(parseFloat(allData.total_worked_hours))
    );
    $(".m-h").html(
      new Intl.NumberFormat().format(parseFloat(allData.missed_hours))
    );
    $(".l-h").html(
      new Intl.NumberFormat().format(parseFloat(allData.hours_leave_days))
    );
    $(".ex-h").html(
      new Intl.NumberFormat().format(parseFloat(allData.expected_hours))
    );
    $(".pub-h").html(
      new Intl.NumberFormat().format(parseFloat(allData.hours_pub_holiday))
    );
    $(".perc-c").html(`${parseFloat(allData.percent_complete).toFixed(2)}%`);

    $(".progress-bar-perc")
      .attr("aria-valuenow", `${allData.percent_complete}`)
      .animate({
        width: $(".progress-bar-perc").attr("aria-valuenow") + "%",
      });
  }

  function populateModal(activityLogsData) {
    var modalBody = $("#activityLogsList");
    modalBody.empty();
    // Extract project name and activity logs from the data
    var name = activityLogsData.name;
    var activityLogs = activityLogsData.activityLogs;
    // Create table element
    var table = $("<table>").addClass("table");

    // Create table head
    var tableHead = $("<thead>").appendTo(table);
    var tableHeadRow = $("<tr>").appendTo(tableHead);
    $("<th>").text("Time Added").appendTo(tableHeadRow);
    $("<th>").text("User").appendTo(tableHeadRow);
    let error = false;
    try {
      error = Boolean(activityLogs[0].project);
    } catch {
      error = false;
    }
    if (error) {
      $("<th>").text("Project").appendTo(tableHeadRow);
    } else {
      $("<th>").text("Activity").appendTo(tableHeadRow);
    }
    $("<th>").text("Date").appendTo(tableHeadRow);
    $("<th>").text("Hours Worked").appendTo(tableHeadRow);
    $("<th>").text("Details").appendTo(tableHeadRow);

    // Create table body
    var tableBody = $("<tbody>").appendTo(table);

    if (activityLogs.length > 0) {
      // Populate table with activity logs
      activityLogs.forEach(function (log) {
        var row = $("<tr>").appendTo(tableBody);
        $("<td>").text(log.time_added).appendTo(row);
        $("<td>").text(log.user).appendTo(row);

        $("<td>")
          .text(log.project ? log.project : log.activity)
          .appendTo(row);
        $("<td>").text(log.date).appendTo(row);
        $("<td>").text(parseFloat(log.hours_worked).toFixed(2)).appendTo(row);
        $("<td>").text(log.details).appendTo(row);
      });
    } else {
      var row = $("<tr>").appendTo(tableBody);
      $("<td>").text("No Data").appendTo(row);
    }
    // Append table to modal body
    modalBody.append(table);

    $("#activityLogsModal .btn-close").click(function () {
      $("#activityLogsModal").modal("hide");
    });

    // Attach downloadExcel function to the download button click event
    $("#downloadExcelBtn").click(function () {
      downloadExcel(activityLogs, name);
    });

    // $("#activityLogsModal").modal("show");
  }

  // Attach event listeners
  $(".card-body-projects, .card-body-activity").on(
    "click",
    ".project-card, .activity-card",
    function () {
      var activityLogs = $(this).data("activityLogs");
      populateModal(activityLogs);
    }
  );

  $("#month-filter, #year-filter, #project-filter").change(function () {
    handleFilterChange();
  });

  handleFilterChange(); // Initial call to load data

  function downloadExcel(activityLogs, name) {
    const csvData = convertToExcel(activityLogs);

    const blob = new Blob([csvData], { type: "text/csv;charset=utf-8" });
    var date = "";

    var usr = user_name;

    const month = $("#month-filter").val();
    const year = $("#year-filter").val();

    if (month == "all") {
      date = year;
    } else {
      date = year + "_" + month;
    }

    const link = document.createElement("a");
    link.href = window.URL.createObjectURL(blob);
    link.download = `activity_logs_${name}_${usr}_${date}.csv`; // Change the file extension to .csv

    document.body.appendChild(link);
    link.click();

    document.body.removeChild(link);
  }

  function convertToExcel(activityLogs) {
    let csvData = "";
    if (activityLogs.length > 0) {
      if (activityLogs[0].project) {
        csvData = "Date,Hours Worked,Project,Details,User\n";
      } else {
        csvData = "Date,Hours Worked,Activity,Details,User\n";
      }
    }
    activityLogs.forEach((log) => {
      if (log.project) {
        csvData += `${log.date},${log.hours_worked},"${log.project}","${log.details}",${log.user}\n`;
      } else {
        csvData += `${log.date},${log.hours_worked},"${log.activity}","${log.details}",${log.user}\n`;
      }
    });

    return csvData;
  }
});
