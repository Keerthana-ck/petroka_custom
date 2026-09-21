# Copyright (c) 2026, Administrator and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 200,
		},
		{
			"fieldname": "task",
			"label": _("Task"),
			"fieldtype": "Link",
			"options": "Task",
			"width": 160,
		},
		{
			"fieldname": "subject",
			"label": _("Subject"),
			"fieldtype": "Data",
			"width": 280,
		},
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 180,
		},
		{
			"fieldname": "expected_hours",
			"label": _("Expected Hours"),
			"fieldtype": "Float",
			"precision": 3,
			"width": 130,
		},
		{
			"fieldname": "actual_hours",
			"label": _("Actual Hours"),
			"fieldtype": "Float",
			"precision": 3,
			"width": 120,
		},
		{
			"fieldname": "employee_working_hours",
			"label": _("Employee Working Hours"),
			"fieldtype": "Float",
			"precision": 3,
			"width": 170,
		},
		{
			"fieldname": "remaining_hours",
			"label": _("Remaining Hours"),
			"fieldtype": "Float",
			"precision": 3,
			"width": 140,
		},
		{
			"fieldname": "total_costing_amount",
			"label": _("Total Costing Amount"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 170,
		},
		{
			"fieldname": "total_billing_amount",
			"label": _("Total Billable Amount"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 170,
		},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"width": 180,
			"hidden": 1,
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 180,
			"hidden": 1,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Data",
			"hidden": 1,
		},
	]


def get_data(filters):
	conditions = [
		"task.project IS NOT NULL",
		"COALESCE(task.is_template, 0) = 0",
	]

	values = {}

	add_date_filters(filters, conditions, values)
	add_link_filters(filters, conditions, values)
	add_status_filters(filters, conditions, values)

	condition_string = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			task.project AS project,
			task.name AS task,
			task.subject AS subject,

			employee.name AS employee,
			employee.department AS department,

			COALESCE(
				task.expected_time,
				0
			) AS expected_hours,

			COALESCE(
				task.actual_time,
				0
			) AS actual_hours,

			COALESCE(
				employee_hours.working_hours,
				0
			) AS employee_working_hours,

			(
				COALESCE(task.expected_time, 0)
				-
				COALESCE(task.actual_time, 0)
			) AS remaining_hours,

			COALESCE(
				task.total_costing_amount,
				0
			) AS total_costing_amount,

			COALESCE(
				task.total_billing_amount,
				0
			) AS total_billing_amount,

			project.company AS company,
			company.default_currency AS currency

		FROM `tabTask` AS task

		LEFT JOIN `tabProject` AS project
			ON project.name = task.project

		LEFT JOIN `tabCompany` AS company
			ON company.name = project.company

		LEFT JOIN (
			SELECT DISTINCT
				reference_name,
				allocated_to

			FROM `tabToDo`

			WHERE
				reference_type = 'Task'
				AND status != 'Cancelled'
		) AS assignment
			ON assignment.reference_name = task.name

		LEFT JOIN `tabEmployee` AS employee
			ON employee.user_id = assignment.allocated_to

		LEFT JOIN (
			SELECT
				timesheet.employee AS employee,
				detail.task AS task,
				SUM(
					COALESCE(detail.hours, 0)
				) AS working_hours

			FROM `tabTimesheet Detail` AS detail

			INNER JOIN `tabTimesheet` AS timesheet
				ON timesheet.name = detail.parent

			WHERE
				timesheet.docstatus = 1
				AND detail.task IS NOT NULL
				AND detail.task != ''

			GROUP BY
				timesheet.employee,
				detail.task
		) AS employee_hours
			ON employee_hours.task = task.name
			AND employee_hours.employee = employee.name

		WHERE {condition_string}

		ORDER BY
			task.project ASC,
			task.exp_start_date ASC,
			task.exp_end_date ASC,
			task.name ASC,
			employee.employee_name ASC
		""",
		values=values,
		as_dict=True,
	)


def add_date_filters(filters, conditions, values):
	if filters.get("start_date"):
		conditions.append(
			"task.exp_start_date >= %(start_date)s"
		)
		values["start_date"] = filters.start_date

	if filters.get("end_date"):
		conditions.append(
			"task.exp_end_date <= %(end_date)s"
		)
		values["end_date"] = filters.end_date


def add_link_filters(filters, conditions, values):
	if filters.get("employee"):
		conditions.append(
			"employee.name = %(employee)s"
		)
		values["employee"] = filters.employee

	if filters.get("department"):
		conditions.append(
			"employee.department = %(department)s"
		)
		values["department"] = filters.department

	if filters.get("project"):
		conditions.append(
			"task.project = %(project)s"
		)
		values["project"] = filters.project

	if filters.get("task"):
		conditions.append(
			"task.name = %(task)s"
		)
		values["task"] = filters.task


def add_status_filters(filters, conditions, values):
	project_statuses = get_multiselect_values(
		filters.get("project_status")
	)

	task_statuses = get_multiselect_values(
		filters.get("task_status")
	)

	if project_statuses:
		conditions.append(
			"project.status IN %(project_statuses)s"
		)
		values["project_statuses"] = tuple(project_statuses)

	if task_statuses:
		conditions.append(
			"task.status IN %(task_statuses)s"
		)
		values["task_statuses"] = tuple(task_statuses)


def get_multiselect_values(value):
	if not value:
		return []

	if isinstance(value, (list, tuple)):
		return [
			item
			for item in value
			if item
		]

	if isinstance(value, str):
		try:
			parsed_value = json.loads(value)

			if isinstance(parsed_value, list):
				return [
					item
					for item in parsed_value
					if item
				]

		except (json.JSONDecodeError, TypeError):
			pass

		return [
			item.strip()
			for item in value.split(",")
			if item.strip()
		]

	return []