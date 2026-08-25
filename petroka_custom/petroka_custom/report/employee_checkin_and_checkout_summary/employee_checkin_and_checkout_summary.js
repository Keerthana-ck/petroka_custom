// Copyright (c) 2026, Administrator and contributors
// For license information, please see license.txt

frappe.query_reports[
	"Employee Checkin and Checkout Summary"] = {
		filters: [
			{
				fieldname: "employee",
				label: __("Employee Name"),
				fieldtype: "Link",
				options: "Employee"
			},
			{
				fieldname: "log_type",
				label: __("Log Type"),
				fieldtype: "Select",
				options: [
					"",
					"IN",
					"OUT"
				]
			},
			{
				fieldname: "from_date",
				label: __("From Date"),
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
				reqd: 1
			},
			{
				fieldname: "to_date",
				label: __("To Date"),
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
				reqd: 1
			}
	],

	formatter(
		value,
		row,
		column,
		data,
		default_formatter
	) {
		value = default_formatter(
			value,
			row,
			column,
			data
		);

		if (
			column.fieldname === "log_type" &&
			data
		) {
			if (data.log_type === "IN") {
				return `
					<span class="indicator-pill green">
						IN
					</span>
				`;
			}

			if (data.log_type === "OUT") {
				return `
					<span class="indicator-pill orange">
						OUT
					</span>
				`;
			}
		}

		return value;
	}
};