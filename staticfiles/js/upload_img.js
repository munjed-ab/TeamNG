document.querySelector(".toast-container").style.display = "none";
function validateFileType() {
  // Get the file input element
  var fileInput = document.getElementById("id_profile_img");
  if (fileInput.files.length === 0) {
    createToast("Please select a file.", "error");
    return false; // Prevent form submission
  }
  var file = fileInput.files[0];

  var allowedExtensions = ["jpg", "jpeg", "png"];
  var fileExtension = file.name.split(".").pop().toLowerCase();

  // Check if the file extension is in the allowed list
  if (!allowedExtensions.includes(fileExtension)) {
    createToast("Only JPEG, JPG, and PNG formats are allowed.", "error");
    return false; // Prevent form submission
  }

  return true;
}

function createToast(message, messageType) {
  const toast = document.querySelector(".toast-container");
  toast.style.display = "block";
  toast.textContent = message;
  toast.style.animation = "fadeOut 3s";

  if (messageType === "success") {
    toast.style.backgroundColor = "green";
  } else if (messageType === "error") {
    toast.style.backgroundColor = "red";
  }

  setTimeout(() => {
    toast.style.animation = "";
    toast.style.display = "none";
  }, 5000);
}
