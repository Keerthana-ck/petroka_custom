// Copyright (c) 2026, Administrator and contributors
// For license information, please see license.txt

frappe.query_reports["Task Summary version-I"] = {
	filters: [
		{
			fieldname: "start_date",
			label: __("Start Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "end_date",
			label: __("End Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",

			get_query() {
				const department =
					frappe.query_report.get_filter_value(
						"department"
					);

				const filters = {
					status: "Active",
				};

				if (department) {
					filters.department = department;
				}

				return {
					filters: filters,
				};
			},
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",

			get_query() {
				const project_statuses =
					frappe.query_report.get_filter_value(
						"project_status"
					);

				const statuses = parse_multiselect_value(
					project_statuses
				);

				if (!statuses.length) {
					return {};
				}

				return {
					filters: {
						status: ["in", statuses],
					},
				};
			},
		},
		{
			fieldname: "task",
			label: __("Task"),
			fieldtype: "Link",
			options: "Task",

			get_query() {
				const project =
					frappe.query_report.get_filter_value(
						"project"
					);

				const task_statuses =
					frappe.query_report.get_filter_value(
						"task_status"
					);

				const statuses = parse_multiselect_value(
					task_statuses
				);

				const filters = {
					is_template: 0,
				};

				if (project) {
					filters.project = project;
				}

				if (statuses.length) {
					filters.status = ["in", statuses];
				}

				return {
					filters: filters,
				};
			},
		},
		{
			fieldname: "project_status",
			label: __("Project Status"),
			fieldtype: "MultiSelectList",
			default: [
				"Open",
				"In Progress",
				"On Hold",
			],

			get_data(txt) {
				return get_status_options(
					[
						"Open",
						"In Progress",
						"On Hold",
						"Completed",
						"Cancelled",
					],
					txt
				);
			},
		},
		{
			fieldname: "task_status",
			label: __("Task Status"),
			fieldtype: "MultiSelectList",
			default: [
				"Open",
				"Working",
				"Pending Review",
				"Overdue",
				"To be Done",
			],

			get_data(txt) {
				return get_status_options(
					[
						"Open",
						"Working",
						"Pending Review",
						"Overdue",
						"To be Done",
						"Completed",
						"Cancelled",
						"Template",
					],
					txt
				);
			},
		},
	],

	onload(report) {
		setup_filter_dependencies(report);
	},
};


function get_status_options(statuses, txt) {
	const search_text = (txt || "")
		.toLowerCase()
		.trim();

	return statuses
		.filter((status) => {
			return status
				.toLowerCase()
				.includes(search_text);
		})
		.map((status) => {
			return {
				value: status,
				description: status,
			};
		});
}


function parse_multiselect_value(value) {
	if (!value) {
		return [];
	}

	if (Array.isArray(value)) {
		return value;
	}

	if (typeof value === "string") {
		try {
			const parsed_value = JSON.parse(value);

			if (Array.isArray(parsed_value)) {
				return parsed_value;
			}
		}
		catch (error) {
			return value
				.split(",")
				.map((item) => item.trim())
				.filter(Boolean);
		}
	}

	return [];
}


function setup_filter_dependencies(report) {
	const department_filter =
		report.get_filter("department");

	const project_filter =
		report.get_filter("project");

	if (department_filter) {
		department_filter.$input.on(
			"change",
			() => {
				report.set_filter_value(
					"employee",
					""
				);
			}
		);
	}

	if (project_filter) {
		project_filter.$input.on(
			"change",
			() => {
				report.set_filter_value(
					"task",
					""
				);
			}
		);
	}
}