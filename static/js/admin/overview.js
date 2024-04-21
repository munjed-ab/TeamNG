const predefinedColors = [
  "#7e8f96",
  "#70798c",
  "#2c3e50",

  "#9a8c98",
  "#ffa69e",
  "#e3c874",

  "#9a8c98",

  "#de4949",
  "#C3ACD0",

  "#1cc88a",
  "RGB(99, 136, 199)",
  "#f6c23e",

  "#9BB0C1",
  "#1cc88a",
  "#B5DDA4",
  "#F8E559",
  "#F9ECCC",
  "magenta",
  "lime",
  "pink",
  "teal",
  "lavender",
  "brown",
  "beige",
  "maroon",
  "olive",
  "coral",
  "navy",
  "grey",
  "black",
];

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
  let chart = null;
  let pieChart = null;
  function handleFilterChange() {
    var month = $("#month-filter").val();
    var year = $("#year-filter").val();
    var user = $("#user-filter").val();
    var department = $("#department-filter").val();
    var project = $("#project-filter").val();

    $.ajax({
      url: "/api/overview_data/",
      method: "GET",
      data: {
        month: month,
        year: year,
        user: user,
        department: department,
        project: project,
      },
      success: function (response) {
        updateProjectCards(response.projects);
        updateActivityChart(response.projects);
        updateActivityCards(response.activities);
        drawChartPie(response.activities);
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

  function updateActivityChart(projects) {
    // Destroy the previous chart if it exists
    if (chart) {
      chart.destroy();
    }

    // Filter out projects with no activity logs
    const projectsWithLogs = projects.filter(
      (project) => project.activity_logs && project.activity_logs.length > 0
    );

    // If there are no projects with activity logs, return
    if (projectsWithLogs.length === 0) {
      return;
    }

    const labels = projectsWithLogs.map((project) => project.name);

    const activityTypeHours = {};

    projectsWithLogs.forEach((project) => {
      const projectData = project.activity_logs;

      // Loop through each activity log in the project
      projectData.forEach((activityLog) => {
        const activityName = activityLog.activity;
        const hoursWorked = parseFloat(activityLog.hours_worked);

        // If activity type doesn't exist in activityTypeHours, initialize it
        if (!activityTypeHours[activityName]) {
          activityTypeHours[activityName] = new Array(labels.length).fill(0);
        }

        // Find the index of the current project in labels
        const projectIndex = labels.indexOf(project.name);

        // Accumulate hours worked for the current activity type and project
        activityTypeHours[activityName][projectIndex] += hoursWorked;
      });
    });

    // Create datasets for each activity type with predefined colors
    const datasets = Object.keys(activityTypeHours).map(
      (activityName, index) => ({
        label: activityName,
        data: activityTypeHours[activityName],
        backgroundColor: predefinedColors[index % predefinedColors.length],
      })
    );

    const data = {
      labels: labels,
      datasets: datasets,
    };

    const ctx = document.getElementById("chart");

    chart = new Chart(ctx, {
      type: "bar",
      data: data,
      options: {
        responsive: true,
        scales: {
          xAxes: [
            {
              stacked: true,
              gridLines: {
                display: false,
              },
            },
          ],
          yAxes: [
            {
              stacked: true,
              ticks: {
                // Include "h" sign in the ticks
                callback: function (value, index, ticks) {
                  return value + " h";
                },
              },
              gridLines: {
                display: false,
              },
            },
          ],
        },
        tooltips: {
          callbacks: {
            label: function (tooltipItem, data) {
              var datasetLabel =
                data.datasets[tooltipItem.datasetIndex].label || "";
              return datasetLabel + ": " + tooltipItem.yLabel + " h";
            },
          },
        },
      },
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

  function drawChartPie(activities) {
    var old_labels = document.getElementById("labels-pie");
    old_labels.innerHTML = "";
    if (pieChart) {
      pieChart.destroy();
    }
    const activitiesWithLogs = activities.filter(
      (activity) => activity.activity_logs && activity.activity_logs.length > 0
    );

    // If there are no projects with activity logs, return
    if (activitiesWithLogs.length === 0) {
      return;
    }

    const labels = activitiesWithLogs.map((activity) => activity.name);
    const percentages = activitiesWithLogs.map((activity) =>
      parseFloat(activity.total).toFixed(2)
    );

    var colors = [];
    for (let i = 0; i < activitiesWithLogs.length; i++) {
      colors.push(predefinedColors[i % predefinedColors.length]);
      $("#labels-pie").append(
        `<span class="col-md-5">
            <i class="fas fa-circle" style="color:${
              predefinedColors[i % predefinedColors.length]
            }"></i> ${activitiesWithLogs[i].name}
          </span>`
      );
    }

    // Set new default font family and font color to mimic Bootstrap's default styling
    (Chart.defaults.global.defaultFontFamily = "Nunito"),
      '-apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif';
    Chart.defaults.global.defaultFontColor = "#858796";

    // Pie Chart Example
    var ctx = document.getElementById("pie-chart");
    pieChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [
          {
            data: percentages,
            backgroundColor: colors,
            hoverBorderColor: "rgba(234, 236, 244, 1)",
          },
        ],
      },
      options: {
        maintainAspectRatio: false,
        tooltips: {
          backgroundColor: "rgb(255,255,255)",
          bodyFontColor: "#858796",
          borderColor: "#dddfeb",
          borderWidth: 1,
          xPadding: 15,
          yPadding: 15,
          displayColors: true,
          caretPadding: 10,
          callbacks: {
            label: function (tooltipItem, data) {
              var label = data.labels[tooltipItem.index] || "";
              var value = data.datasets[0].data[tooltipItem.index];
              return label + ": " + value + " h";
            },
          },
        },
        legend: {
          display: false,
        },
        cutoutPercentage: 80,
      },
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

    // Append table to modal body
    modalBody.append(table);

    $("#activityLogsModal .btn-close").click(function () {
      $("#activityLogsModal").modal("hide");
    });

    // Attach downloadExcel function to the download button click event
    $("#downloadExcelBtn").click(function () {
      downloadExcel(activityLogs, name);
    });

    $("#activityLogsModal").modal("show");
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

  handleFilterChange(); // Initial call to load data

  function downloadExcel(activityLogs, name) {
    const csvData = convertToExcel(activityLogs);

    const blob = new Blob([csvData], { type: "text/csv;charset=utf-8" });
    var date = "";
    var dept = "";
    var usr = "";

    const month = $("#month-filter").val();
    const year = $("#year-filter").val();
    const department = $("#department-filter").val();

    if (month == "all") {
      date = year;
    } else {
      date = year + "_" + month;
    }
    if (department == "all") {
      dept = "_";
    } else {
      dept = department;
    }

    const link = document.createElement("a");
    link.href = window.URL.createObjectURL(blob);
    link.download = `activity_logs_${name}_${dept}_${date}.csv`; // Change the file extension to .csv

    document.body.appendChild(link);
    link.click();

    document.body.removeChild(link);
  }

  function convertToExcel(activityLogs) {
    let csvData = "";
    if (activityLogs[0].project) {
      csvData = "Date,Hours Worked,Project,Details,User\n";
    } else {
      csvData = "Date,Hours Worked,Activity,Details,User\n";
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
