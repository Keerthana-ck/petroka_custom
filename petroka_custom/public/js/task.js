frappe.ui.form.on("Task", {
	setup(frm) {
		frm.set_query("custom_task_assign_to", () => {
			return {
				filters: {
					status: "Active",
				},
			};
		});
	}
});