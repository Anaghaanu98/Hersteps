
document.addEventListener("DOMContentLoaded", function () {
    const editButton = document.getElementById("editDetailsBtn");
    const saveButton = document.getElementById("saveChangesBtn");
    const profileForm = document.getElementById("profileForm");

    if (!editButton || !saveButton || !profileForm) {
        console.error("Profile elements not found.");
        return;
    }

    const editableFields = [
        "fullname",
        "username",
        "phone_number"
    ];

    // Fields are initially read-only
    saveButton.disabled = true;

    // Enable editing when Edit Details is clicked
    editButton.addEventListener("click", function () {
        editableFields.forEach(function (fieldId) {
            const field = document.getElementById(fieldId);

            if (field) {
                field.removeAttribute("readonly");
                field.readOnly = false;
            }
        });

        saveButton.disabled = false;
        editButton.textContent = "Editing Details";
    });
});
