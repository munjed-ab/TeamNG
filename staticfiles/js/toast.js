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
