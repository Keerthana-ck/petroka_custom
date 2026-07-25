# Copyright (c) 2026, Administrator and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}

	columns = get_columns()

	data = frappe.db.get_all(
		"Project",
		filters=filters,
		fields=[
			"name",
			"project_name",
			"status",
			"percent_complete",
			"expected_start_date",
			"expected_end_date",
			"project_type",
		],
		order_by="expected_end_date",
	)

	task_summary = get_task_summary(data)

	for project in data:
		project_task_summary = task_summary.get(project.name, {})

		project["total_tasks"] = project_task_summary.get("total_tasks", 0)
		project["completed_tasks"] = project_task_summary.get(
			"completed_tasks", 0
		)
		project["overdue_tasks"] = project_task_summary.get(
			"overdue_tasks", 0
		)
		project["total_costing_amount"] = project_task_summary.get(
			"total_costing_amount", 0
		)
		project["total_billing_amount"] = project_task_summary.get(
			"total_billing_amount", 0
		)

	chart = get_chart_data(data)
	report_summary = get_report_summary(data)

	return columns, data, None, chart, report_summary


def get_task_summary(projects):
	"""
	Get task counts, costing and billing amounts grouped by Project.
	"""

	project_names = [project.name for project in projects]

	if not project_names:
		return {}

	task_data = frappe.db.sql(
		"""
		SELECT
			project,
			COUNT(name) AS total_tasks,

			SUM(
				CASE
					WHEN status = 'Completed' THEN 1
					ELSE 0
				END
			) AS completed_tasks,

			SUM(
				CASE
					WHEN status = 'Overdue' THEN 1
					ELSE 0
				END
			) AS overdue_tasks,

			SUM(
				COALESCE(total_costing_amount, 0)
			) AS total_costing_amount,

			SUM(
				COALESCE(total_billing_amount, 0)
			) AS total_billing_amount

		FROM `tabTask`

		WHERE project IN %(project_names)s

		GROUP BY project
		""",
		{
			"project_names": tuple(project_names),
		},
		as_dict=True,
	)

	return {
		row.project: row
		for row in task_data
	}


def get_columns():
	return [
		{
			"fieldname": "name",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 200,
		},
		{
			"fieldname": "project_name",
			"label": _("Project Name"),
			"width": 200,
		},
		{
			"fieldname": "project_type",
			"label": _("Type"),
			"fieldtype": "Link",
			"options": "Project Type",
			"width": 120,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "total_tasks",
			"label": _("Total Tasks"),
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "completed_tasks",
			"label": _("Tasks Completed"),
			"fieldtype": "Int",
			"width": 130,
		},
		{
			"fieldname": "overdue_tasks",
			"label": _("Tasks Overdue"),
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "total_costing_amount",
			"label": _("Total Costing Amount"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 160,
		},
		{
			"fieldname": "total_billing_amount",
			"label": _("Total Billing Amount"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 160,
		},
		{
			"fieldname": "percent_complete",
			"label": _("Completion"),
			"fieldtype": "Percent",
			"width": 120,
		},
		{
			"fieldname": "expected_start_date",
			"label": _("Start Date"),
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"fieldname": "expected_end_date",
			"label": _("End Date"),
			"fieldtype": "Date",
			"width": 120,
		},
	]


def get_chart_data(data):
	labels = []
	total = []
	completed = []
	overdue = []

	for project in data:
		labels.append(project.project_name or project.name)
		total.append(project.total_tasks or 0)
		completed.append(project.completed_tasks or 0)
		overdue.append(project.overdue_tasks or 0)

	return {
		"data": {
			"labels": labels[:30],
			"datasets": [
				{
					"name": _("Overdue"),
					"values": overdue[:30],
				},
				{
					"name": _("Completed"),
					"values": completed[:30],
				},
				{
					"name": _("Total Tasks"),
					"values": total[:30],
				},
			],
		},
		"type": "bar",
		"colors": [
			"#fc4f51",
			"#78d6ff",
			"#7575ff",
		],
		"barOptions": {
			"stacked": True,
		},
	}


def get_report_summary(data):
	if not data:
		return None

	avg_completion = (
		sum((project.percent_complete or 0) for project in data)
		/ len(data)
	)

	total_tasks = sum(
		(project.total_tasks or 0)
		for project in data
	)

	completed_tasks = sum(
		(project.completed_tasks or 0)
		for project in data
	)

	overdue_tasks = sum(
		(project.overdue_tasks or 0)
		for project in data
	)

	return [
		{
			"value": avg_completion,
			"indicator": (
				"Green"
				if avg_completion > 50
				else "Red"
			),
			"label": _("Average Completion"),
			"datatype": "Percent",
		},
		{
			"value": total_tasks,
			"indicator": "Blue",
			"label": _("Total Tasks"),
			"datatype": "Int",
		},
		{
			"value": completed_tasks,
			"indicator": "Green",
			"label": _("Completed Tasks"),
			"datatype": "Int",
		},
		{
			"value": overdue_tasks,
			"indicator": (
				"Green"
				if overdue_tasks == 0
				else "Red"
			),
			"label": _("Overdue Tasks"),
			"datatype": "Int",
		},
	]