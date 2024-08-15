flatpickr("#startDate", {
  dateFormat: "Y-m-d",
  minDate: "",
  onClose: function (selectedDates, dateStr, instance) {
    const endDatePicker = document.getElementById("endDate")._flatpickr;
    if (endDatePicker) {
      endDatePicker.set("minDate", dateStr);
    }
  },
  onChange: function (selectedDates, dateStr, instance) {
    const endDatePicker = document.getElementById("endDate")._flatpickr;
    if (endDatePicker) {
      // Update minDate of endDatePicker to be the next day of startDate
      endDatePicker.set("minDate", new Date(selectedDates[0]).fp_incr(1));
    }
  },
});

flatpickr("#endDate", {
  dateFormat: "Y-m-d",
  minDate: "today",
  onClose: function (selectedDates, dateStr, instance) {
    const startDatePicker = document.getElementById("startDate")._flatpickr;
    if (startDatePicker) {
      startDatePicker.set("maxDate", dateStr);
    }
  },
  onChange: function (selectedDates, dateStr, instance) {
    const startDatePicker = document.getElementById("startDate")._flatpickr;
    if (startDatePicker) {
      // Update maxDate of startDatePicker to be the previous day of endDate
      startDatePicker.set("maxDate", new Date(selectedDates[0]).fp_incr(-1));
    }
  },
});

function validateForm() {
  var inputs = document.querySelectorAll("input, select, textarea");

  var isValid = true;

  inputs.forEach(function (input) {
    if (!input.value.trim()) {
      isValid = false;
    }
  });

  return isValid;
}

document
  .getElementById("addleave")
  .addEventListener("submit", function (event) {
    if (!validateForm()) {
      event.preventDefault();
      alert("Please fill in all required fields.");
    }
  });
