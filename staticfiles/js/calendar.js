const daily_hours = JSON.parse(
  document.getElementById("daily_hours").textContent
);

async function updateCalendar(calendar, start, end) {
  let startMonth = start.getMonth() + 1;
  let startYear = start.getFullYear();
  try {
    let data = await $.ajax({
      url: "/apis/get_calendar_data/",
      method: "GET",
      mode: "same-origin",
      data: { year: startYear, month: startMonth },
      beforeSend: function (xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
          xhr.setRequestHeader("X-CSRFToken", getCookie("csrftoken"));
        }
      },
    });

    // Clear events from the previous month

    calendar.getEvents().forEach((event) => event.remove());

    // Fetch holiday data for all dates in the current month
    let holidayData = await fetchHolidayData(Object.keys(data));
    let leaveData = await fetchLeaveData(Object.keys(data));
    // Add events for the current month
    for (let date in data) {
      let hoursWorked = parseFloat(data[date]);
      let eventTitle = hoursWorked + "h";
      if (leaveData[date]) {
        calendar.addEvent({
          title: "leave",
          start: date,
          backgroundColor: "rgb(49, 97, 120)",
          textColor: "white",
          borderColor: "#2c3e50",
        });
      }
      if (holidayData[date]) {
        calendar.addEvent({
          title: holidayData[date],
          start: date,
          backgroundColor: "rgb(173, 46, 42)",
          textColor: "white",
          borderColor: "#2c3e50",
        });
      } else if (!leaveData[date]) {
        calendar.addEvent({
          title: eventTitle,
          start: date,
          url: `../register-hours/${date}`,
          color: "white",
          borderColor: "#2c3e50",
        });
      }
    }
  } catch (error) {
    console.error("Error updating calendar:", error);
  }
}

// Function to fetch holiday data for multiple dates
async function fetchHolidayData(dates) {
  try {
    let response = await $.ajax({
      url: "/apis/calendar_holiday_data/",
      method: "GET",
      mode: "same-origin",
      data: { dates: dates },
    });

    return response;
  } catch (error) {
    console.error("Error fetching holiday data:", error);
    return {};
  }
}

async function fetchLeaveData(dates) {
  try {
    let response = await $.ajax({
      url: "/apis/calendar_leave_data/",
      method: "GET",
      mode: "same-origin",
      data: { dates: dates },
    });

    return response;
  } catch (error) {
    console.error("Error fetching leave data:", error);
    return {};
  }
}

// Initialize the fullcalendar
document.addEventListener("DOMContentLoaded", function () {
  let calendarEl = document.getElementById("calendar");
  let calendar = new FullCalendar.Calendar(calendarEl, {
    eventDidMount: function (info) {
      setColorGradient(info);
      checkWeekDays(info);
    },

    dayCellDidMount: function (arg) {
      const dayOfWeek = arg.date.getDay();
      const dayOfMonth = arg.date.getDate();
      const eventEl = arg.el;
      if (dayOfWeek === 0) {
        eventEl.style.backgroundColor = "rgb(222 223 233)"; //rgb(209, 153, 153) #f7f9ff rgb(222 223 233)
        eventEl.add;
      }

      if (
        dayOfWeek === 6 &&
        ((dayOfMonth > 7 && dayOfMonth <= 14) ||
          (dayOfMonth > 21 && dayOfMonth <= 28))
      ) {
        eventEl.style.backgroundColor = "rgb(222 223 233)";
      }
    },
    headerToolbar: {
      start: "today",
      center: "title",
      end: "prev,next", // Remove the "Today" button
    },
  });

  // Render the calendar
  calendar.render();

  let currentDate = calendar.getDate();
  updateCalendar(calendar, currentDate, currentDate);

  document
    .querySelector(".fc-prev-button")
    .addEventListener("click", function () {
      let newDate = calendar.getDate();
      updateCalendar(calendar, newDate, newDate);
    });

  document
    .querySelector(".fc-next-button")
    .addEventListener("click", function () {
      let newDate = calendar.getDate();
      updateCalendar(calendar, newDate, newDate);
    });
  document
    .querySelector(".fc-today-button")
    .addEventListener("click", function () {
      let newDate = calendar.getDate();
      updateCalendar(calendar, newDate, newDate);
    });
  //TODO :[Violation] Added non-passive event listener to a scroll-blocking 'touchmove' event.
  //Consider marking event handler as 'passive' to make the page more responsive.
  //See https://www.chromestatus.com/feature/5745543795965952
  //Pa.handleTouchStart	@	index.global.min.js:9275
});
/**
 * Checks if the event falls on a weekend and within certain date ranges, then removes the event.
 *
 * @param {object} info - the event information
 * @return {void}
 */
function checkWeekDays(info) {
  const eventDate = info.event.start;
  const dayOfWeek = eventDate.getDay();
  const dayOfMonth = eventDate.getDate();
  const eventEl = info.el;
  const event = info.event;

  // Check if it's Sunday or Saturday on the 2nd and 4th weeks of the month
  if (
    dayOfWeek === 0 ||
    (dayOfWeek === 6 &&
      ((dayOfMonth > 7 && dayOfMonth <= 14) ||
        (dayOfMonth > 21 && dayOfMonth <= 28)))
  ) {
    // Set background color to red
    // Set event title to 'holiday'
    if (event.title != "leave") {
      event.remove();
    }
    // Indicate that the event has been modified
  }
}

/**
 * Set color gradient for the event element based on the hours worked.
 *
 * @param {object} info - The information object containing the event element and title
 * @return {void}
 */
function setColorGradient(info) {
  const eventEl = info.el;
  let str = info.event.title;
  str = str.slice(0, -1);
  let isnum = /^[\d.]+$/.test(str);

  if (isnum) {
    const hoursWorked = parseFloat(info.event.title);
    const color = calculateColor(hoursWorked);
    eventEl.style.backgroundColor = color;
    eventEl.style.textAlign = "center";
    eventEl.style.fontSize = "18px";
  } else {
    eventEl.style.textAlign = "center";
    eventEl.style.fontSize = "18px";
  }
}

/**
 * Calculates the color based on a percentage. rgb(20, 20, 20)
 *
 * @param {number} hoursWorked - The hoursWorked to calculate the color.
 * @return {string} The calculated color in the format "rgb(r, g, b)".
 */
function calculateColor(hoursWorked) {
  const least = [113, 155, 161]; //rgb(99 139 145) old:140, 199, 207 ,,new rgb(127 148 151)
  const middle = [99, 136, 199];
  const most = [43, 166, 98];

  if (hoursWorked === 0) {
    return `rgb(${least[0]}, ${least[1]}, ${least[2]})`;
  } else if (hoursWorked > 0 && hoursWorked < daily_hours) {
    return `rgb(${middle[0]}, ${middle[1]}, ${middle[2]})`;
  } else {
    return `rgb(${most[0]}, ${most[1]}, ${most[2]})`;
  }
}

function csrfSafeMethod(method) {
  return /^(GET|HEAD|OPTIONS|TRACE)$/.test(method);
}

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

function checkPastFutureDates(info, calendar) {
  // NOT USED ..
  const currentDate = new Date();
  const currentDayOfMonth = currentDate.getDate();
  const currentMonth = currentDate.getMonth() + 1; // Months are zero-indexed
  const currentYear = currentDate.getFullYear(); // Get the current year

  const eventDate = info.event.start;
  const eventDayOfMonth = eventDate.getDate();
  const eventMonth = eventDate.getMonth() + 1; // Months are zero-indexed
  const eventYear = eventDate.getFullYear(); // Get the event year

  if (currentDayOfMonth <= 11) {
    // If today is less than or equal to the 11th day of the month
    if (currentMonth === 1) {
      // If the current month is January
      if (eventYear < currentYear) {
        // If the event year is before the current year
        info.event.remove();
      }
    } else {
      // If the current month is not January
      if (eventYear < currentYear || eventMonth < currentMonth - 1) {
        // If the event year is before the current year
        // Or if the event month is before the previous month
        info.event.remove();
      }
    }
  } else {
    // If today is greater than the 11th day of the month
    if (eventYear < currentYear || eventMonth !== currentMonth) {
      // If the event year is before the current year
      // Or if the event month is not the current month
      info.event.remove();
    }
  }
}
