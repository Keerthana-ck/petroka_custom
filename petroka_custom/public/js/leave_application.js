frappe.ui.form.on("Leave Application", {
	employee(frm) {
		fetch_employee_eid(frm);
	}
});

async function fetch_employee_eid(frm) {
	const employee_name = frm.doc.employee;

	// Clear the previous employee's EID.
	await frm.set_value("custom_eid", "");

	if (!employee_name) {
		return;
	}

	try {
		const employee_doc = await frappe.db.get_doc(
			"Employee",
			employee_name
		);

		// Prevent setting the wrong EID if the employee was changed
		// before the request completed.
		if (frm.doc.employee !== employee_name) {
			return;
		}

		const current_documents =
			employee_doc.custom_document_expiry_details || [];

		const expired_documents =
			employee_doc.custom_expired_employee_document || [];

		// Current documents are checked first.
		const all_documents = [
			...current_documents,
			...expired_documents
		];

		const eid_row = all_documents.find(row => {
			return String(row.document_name || "")
				.trim()
				.toUpperCase() === "EID";
		});

		if (eid_row && eid_row.document_number) {
			await frm.set_value(
				"custom_eid",
				eid_row.document_number
			);
		} else {
			frappe.show_alert({
				message: __("EID document was not found for this employee."),
				indicator: "orange"
			});
		}

	} catch (error) {
		console.error("Error fetching employee EID:", error);

		frappe.msgprint({
			title: __("Unable to Fetch EID"),
			message: __(
				"An error occurred while fetching the EID from the Employee master."
			),
			indicator: "red"
		});
	}
}