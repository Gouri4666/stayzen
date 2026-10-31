document.addEventListener("DOMContentLoaded", function () {

    const uniqueValidationFields = [
        {
            inputId: "id_room_number",
            itemType: "room",
            label: "Room Number"
        },
        {
            inputId: "id_hall_name",
            itemType: "event",
            label: "Hall Name"
        },
        {
            inputId: "id_table_number",
            itemType: "table",
            label: "Table Number"
        },
        {
            inputId: "id_package_name",
            itemType: "package",
            label: "Package Name"
        },
        {
            inputId: "id_item_name",
            itemType: "food",
            label: "Food Item Name"
        }
    ];

    const submitButton = document.querySelector('form button[type="submit"]');

    uniqueValidationFields.forEach(field => {

        const input = document.getElementById(field.inputId);

        if (!input) return;

        let validationMessage = document.createElement("div");
        validationMessage.className = "text-danger mt-1";
        validationMessage.style.fontSize = "0.85rem";
        validationMessage.style.display = "none";

        input.parentNode.appendChild(validationMessage);

        let debounceTimer;

        input.addEventListener("input", function () {

            clearTimeout(debounceTimer);

            const value = input.value.trim();

            if (value === "") {
                input.classList.remove("is-invalid");
                validationMessage.style.display = "none";

                if (submitButton)
                    submitButton.disabled = false;

                return;
            }

            debounceTimer = setTimeout(function () {

                fetch(`/admin-panel/validate-unique-item/?item_type=${field.itemType}&value=${encodeURIComponent(value)}`)
                    .then(response => response.json())
                    .then(data => {

                        if (data.exists) {

                            input.classList.add("is-invalid");

                            validationMessage.textContent = `This ${field.label} already exists.`;
                            validationMessage.style.display = "block";

                            if (submitButton)
                                submitButton.disabled = true;

                        } else {

                            input.classList.remove("is-invalid");

                            validationMessage.style.display = "none";

                            if (submitButton)
                                submitButton.disabled = false;
                        }

                    })
                    .catch(() => {
                        input.classList.remove("is-invalid");
                        validationMessage.style.display = "none";

                        if (submitButton)
                            submitButton.disabled = false;
                    });

            }, 300);

        });

    });

});