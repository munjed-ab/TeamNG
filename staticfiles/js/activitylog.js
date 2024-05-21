$(document).ready(function () {
  // Initialize Flatpickr datepicker
  flatpickr("#q", {
    dateFormat: "Y-m-d", // Set date format
    maxDate: "today",
    onChange: function (selectedDates, dateStr, instance) {
      // Trigger form submission when date is selected
      document.getElementById("date-form").submit();
    },
  });
});
