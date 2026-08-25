frappe.ui.form.on("Expense Claim", {
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
