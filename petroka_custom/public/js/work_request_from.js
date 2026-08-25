frappe.ui.form.on("Work Request Form", {
	setup(frm) {
		frm.set_query("employee", () => {
			return {
				filters: {
					status: "Active",
				},
			};
		});
	}
});