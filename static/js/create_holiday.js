$(document).ready(function () {
  var form_fields = document.getElementsByTagName("input");
  form_fields[1].placeholder = "Enter holiday name..";
  // Initialize Flatpickr datepicker
  flatpickr("#holiday_date", {
    dateFormat: "Y-m-d", // Set date format
    disable: [
      function (date) {
        // Disable Sundays (0 is Sunday, 1 is Monday, ..., 6 is Saturday)
        if (date.getDay() === 0) return true;

        // Disable the second and fourth Saturdays
        if (date.getDay() === 6) {
          var weekOfMonth = Math.floor((date.getDate() - 1) / 7) + 1;
          if (weekOfMonth === 2 || weekOfMonth === 4) {
            return true;
          }
        }
      },
    ],
  });
});
