frappe.ui.form.on("Work Request Form", {
    async onload(frm) {
        if (!frm.is_new()) {
            return;
        }

        // Remove the default Company applied by User Defaults.
        await frm.set_value({
            employee: "",
            company: "",
            email: ""
        });

        try {
            const response = await frm.call(
                "get_logged_in_employee_details"
            );

            const details = response.message;

            if (!details) {
                frappe.show_alert({
                    message: __("No active Employee is linked to this user."),
                    indicator: "orange"
                });
                return;
            }

            // Setting Employee will also trigger any Fetch From fields
            // such as designation, department, phone and joining date.
            await frm.set_value(
                "employee",
                details.employee
            );

            await frm.set_value(
                "company",
                details.company || ""
            );

            await frm.set_value(
                "email",
                details.email || ""
            );

        } catch (error) {
            console.error(
                "Unable to fetch logged-in Employee details:",
                error
            );
        }
    }
});