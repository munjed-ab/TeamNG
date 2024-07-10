$(document).ready(function () {
  $(".response-btn").click(function () {
    var leaveId = $(this).data("leaveid");

    var response = $(this).data("response");

    $("#leaveRequestId").val(leaveId);
    $("#response").val(response);

    var message = response === "approved" ? "Accept request" : "Reject request";
    $("#responseMessage").text(message);
    $("#responseModal").modal("show");
  });

  $("#responseForm").submit(function (event) {
    event.preventDefault();

    $.ajax({
      url: "/notifications/",
      method: "POST",
      data: $(this).serialize(),
      success: function (response) {
        console.log("Response submitted successfully");
        location.reload();
        $("#responseModal").modal("hide"); // Close the modal after successful submission
      },
      error: function (xhr, status, error) {
        console.error("Error occurred while submitting response:", error);
        alert("Error occurred while submitting response. Please try again.");
      },
    });
  });
});
// Function to handle closing the modal
function closeModal() {
  $("#responseModal").modal("hide");
}

// Event listener for clicking the close button
$("#responseModal .close").click(function () {
  closeModal();
});

// Event listener for clicking the exit icon
$("#responseModal").on("click", "[data-dismiss='modal']", function () {
  closeModal();
});
