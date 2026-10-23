
const profileToggle = document.getElementById("profileToggle");
const profileDropdown = document.getElementById("profileDropdown");

if (profileToggle && profileDropdown) {
    profileToggle.addEventListener("click", function () {
        const isCurrentlyOpen = !profileDropdown.hidden;

        profileDropdown.hidden = isCurrentlyOpen;

        profileToggle.setAttribute(
            "aria-expanded",
            String(!isCurrentlyOpen)
        );
    });

    document.addEventListener("click", function (event) {
        if (!event.target.closest(".profile-area")) {
            profileDropdown.hidden = true;
            profileToggle.setAttribute("aria-expanded", "false");
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            profileDropdown.hidden = true;
            profileToggle.setAttribute("aria-expanded", "false");
            profileToggle.focus();
        }
    });
}