// Copyright (c) 2026, Administrator and contributors
// For license information, please see license.txt

frappe.query_reports["Compensatory Off Summary"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today()
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company")
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",

			get_query() {
				const company =
					frappe.query_report.get_filter_value("company");

				const filters = {
					status: "Active"
				};

				if (company) {
					filters.company = company;
				}

				return {
					filters: filters
				};
			}
		}
	]
};
