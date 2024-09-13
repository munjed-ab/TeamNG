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
      // Allow same date selection, but ensure endDate is not before startDate
      endDatePicker.set("minDate", dateStr);

      // If endDate is now invalid, update it to match startDate
      if (endDatePicker.selectedDates[0] < selectedDates[0]) {
        endDatePicker.setDate(dateStr);
      }
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
      // Allow same date selection, but ensure startDate is not after endDate
      startDatePicker.set("maxDate", dateStr);

      // If startDate is now invalid, update it to match endDate
      if (startDatePicker.selectedDates[0] > selectedDates[0]) {
        startDatePicker.setDate(dateStr);
      }
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
