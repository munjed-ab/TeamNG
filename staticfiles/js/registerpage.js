function isTableEmpty() {
  if ($(".new-entries").children().length === 0) {
    document.getElementById("save-button").style.display = "none";
  } else {
    document.getElementById("save-button").style.display = "inline-block";
  }
}

function escapeHtml(text) {
  var map = {
    "<": "&lt;",
    ">": "&gt;",
  };
  return text.replace(/[<>]/g, function (m) {
    return map[m];
  });
}
isTableEmpty();

var details = document.getElementById("details");
details.value = "";
const total_hours_stored = JSON.parse(
  document.getElementById("total").textContent
);
const schema = JSON.parse(document.getElementById("scheme").textContent);
const host = JSON.parse(document.getElementById("get_host").textContent);
var total_hours = parseFloat(total_hours_stored);
let data = [];
const daily_hours = JSON.parse(
  document.getElementById("daily_hours").textContent
);

$(document).ready(function () {
  $("#addactivity").click(function () {
    var projectName = $("#projectName").val();
    var activityName = $("#activityName").val();
    if (!projectName || !activityName) {
      createToast(`Please enter a Project and an Activity type.`, "error");
      $("#quantity").val("");
      return;
    }
    var date = JSON.parse(document.getElementById("date").textContent);
    var details = escapeHtml($("#details").val());
    var hours = $("#quantity").val();
    var countdigits = hours.length;
    if (
      !hours ||
      isNaN(parseFloat(hours)) ||
      parseFloat(hours) < 0 ||
      parseFloat(hours) > parseFloat(daily_hours)
    ) {
      createToast(
        `Please enter a number between 0 and ${parseFloat(daily_hours)}.`,
        "error"
      );
      $("#quantity").val("");
      return;
    } else if (countdigits > 4) {
      createToast(`Too many digits entered.`, "error");
      $("#quantity").val("");
      return;
    }
    if (total_hours + parseFloat(hours) > parseFloat(daily_hours)) {
      createToast(`You exeeded the ${parseFloat(daily_hours)} hours`, "error");
      $("#details").val("");
      $("#quantity").val("");
      return;
    }
    total_hours += parseFloat(hours);
    document.getElementById("total-hours").innerHTML = `${total_hours}h`;
    let activityLog = {
      project: projectName,
      activity: activityName,
      date: date,
      details: details,
      hours: hours,
    };

    data.push(activityLog);
    //localStorage.setItem("activityData", JSON.stringify(data));

    $(".new-entries").append(
      "<tr>" +
        "<td>" +
        projectName +
        "</td> " +
        "<td>" +
        activityName +
        "</td>" +
        "<td>" +
        hours +
        "h</td>" +
        "<td>" +
        date +
        "</td>" +
        "<td>" +
        details +
        "</td>" +
        "<td> <div class='row'> <div class='update-icon col-sm-6 col-xs-6 editBtn'> <i class='fas fa-pencil-alt mr-2 text-primary fa-1x'></i> </div><div class='col-sm-6 col-xs-6 delete-icon deleteBtn'><i class='fas fa-trash-alt mr-5 text-danger fa-1x'></i></div> </div></td>" +
        "</tr>"
    );
    document.getElementById("save-button").style.display = "inline-block";
    $("#details").val("");
    $("#quantity").val("");
    $("#activityName").val("");
    $("#projectName").val("");
  });

  $(document).on("click", ".deleteBtn", function () {
    var row = $(this).closest("tr");
    var rowIndex = row.index();
    var hours = row.find("td:eq(2)").text().replace("h", "");
    total_hours -= parseFloat(hours);
    document.getElementById("total-hours").innerHTML = `${total_hours}h`;
    $(this).closest("tr").remove();
    data.splice(rowIndex, 1);
    isTableEmpty();
    //localStorage.removeItem("activityData", JSON.stringify(data));
  });

  $(document).on("click", ".editBtn", function () {
    var row = $(this).closest("tr");
    var rowIndex = row.index();
    var projectName = row.find("td:eq(0)").text();
    var activityName = row.find("td:eq(1)").text();
    var hours = row.find("td:eq(2)").text().replace("h", "");
    var date = row.find("td:eq(3)").text();
    var details = row.find("td:eq(4)").text();
    total_hours -= parseFloat(hours);
    document.getElementById("total-hours").innerHTML = `${total_hours}h`;
    $("#projectName").val(projectName);
    $("#activityName").val(activityName);
    $("#quantity").val(hours);
    $("#details").val(details);
    row.remove();
    data.splice(rowIndex, 1);
    isTableEmpty();
  });

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  $("#save-button").click(function () {
    const csrftoken = getCookie("csrftoken");
    var requestBody = {
      data: JSON.stringify(data),
    };
    // const BASE_URL = `${schema}://${host}/`;
    // const API_URL = BASE_URL + "apis/post_activity_data/";
    // const request = new Request(API_URL, {
    //   headers: { "X-CSRFToken": csrftoken, "Content-Type": "application/json" },
    // });

    // fetch(request, {
    //   method: "POST",
    //   mode: "same-origin",
    //   body: JSON.stringify(data),
    // })
    //   .then((response) => {
    //     if (!response.ok) {
    //       throw new Error("Network response was not ok");
    //     }
    //     return response.json();
    //   })
    //   .then((data) => {
    //     // Clear data array
    //     data = [];
    //     //  localStorage.removeItem("activityData");
    //     location.reload();
    //   })
    //   .catch(function (error) {
    //     console.error("Error saving data:", error);
    //   });

    var headers = new Headers();
    headers.append("Content-Type", "application/json");
    headers.append("X-CSRFToken", csrftoken);

    var requestBody = {
      data: JSON.stringify(data),
    };

    fetch("/apis/post_activity_data/", {
      method: "POST",
      mode: "same-origin",
      headers: headers,
      body: JSON.stringify(requestBody),
    })
      .then(function (response) {
        if (!response.ok) {
          location.reload();
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then(function (data) {
        // Clear data array
        data = [];
        //  localStorage.removeItem("activityData");
        location.reload();
      })
      .catch(function (error) {
        console.error("Error saving data:", error);
        location.reload();
      });
  });

  /*
    var storedData = localStorage.getItem("activityData");
    if (storedData) {
      data = JSON.parse(storedData);
      data.forEach(function (entry) {
        $(".content").append(
          "<tr class='newdata'>" +
            "<td>" +
            entry.project +
            "</td>" +
            "<td>" +
            entry.activity +
            "</td>" +
            "<td>" +
            entry.hours +
            "h</td>" +
            "<td>" +
            entry.date +
            "</td>" +
            "<td>" +
            entry.details +
            "</td>" +
            "<td><button class='deleteBtn'>Delete</button></td>" +
            "</tr>"
        );
      });
    }
    */
});

function checkNumberValidity() {
  var numberInput = document.getElementById("quantity");
  var userInput = parseFloat(numberInput.value);

  if (userInput < 0 || userInput > parseFloat(daily_hours)) {
    createToast(
      `Please enter a number between 0 and ${parseFloat(daily_hours)}.`,
      "error"
    );
    numberInput.value = "";
  }
}
