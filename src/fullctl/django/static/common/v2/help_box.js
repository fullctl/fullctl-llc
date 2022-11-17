document.addEventListener("DOMContentLoaded", () => {
  const help_button = document.querySelector(".help-btn");
  const box = document.querySelector(".help-box");

  help_button.addEventListener('click', () => {
    box.classList.remove("js-hide");
    box.style.bottom = help_button.getBoundingClientRect().bottom - help_button.getBoundingClientRect().top + "px";
  })



  document.addEventListener("click", (event) => {
    if (event.target.closest(".help-box")) return;
    if (event.target.closest(".help-btn")) return;
    box.classList.add("js-hide");
  })
});
