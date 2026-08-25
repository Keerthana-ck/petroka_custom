# Copyright (c) 2026, Administrator and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	get_datetime,
	getdate,
	today,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})

	from_date = getdate(
		filters.get("from_date") or today()
	)

	to_date = getdate(
		filters.get("to_date") or today()
	)

	validate_filters(from_date, to_date)

	columns = get_columns()

	data = get_data(
		filters=filters,
		from_date=from_date,
		to_date=to_date,
	)

	return columns, data


def validate_filters(from_date, to_date):
	if from_date > to_date:
		frappe.throw(
			_("From Date cannot be after To Date.")
		)


def get_columns():
	return [
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Time"),
			"fieldname": "time",
			"fieldtype": "Time",
			"width": 120,
		},
		{
			"label": _("Log Type"),
			"fieldname": "log_type",
			"fieldtype": "Data",
			"width": 110,
		},
	]


def get_data(filters, from_date, to_date):
	conditions = []

	values = {
		"from_datetime": get_datetime(from_date),
		"to_datetime": get_datetime(
			add_days(to_date, 1)
		),
	}

	if filters.get("employee"):
		conditions.append(
			"AND checkin.employee = %(employee)s"
		)

		values["employee"] = filters.employee

	if filters.get("log_type"):
		conditions.append(
			"AND checkin.log_type = %(log_type)s"
		)

		values["log_type"] = filters.log_type

	condition_sql = "\n".join(conditions)

	checkin_records = frappe.db.sql(
		f"""
			SELECT
				checkin.employee,
				checkin.employee_name,
				checkin.time AS checkin_time,
				checkin.log_type
			FROM
				`tabEmployee Checkin` AS checkin
			WHERE
				checkin.time >= %(from_datetime)s
				AND checkin.time < %(to_datetime)s
				{condition_sql}
			ORDER BY
				checkin.time ASC
		""",
		values=values,
		as_dict=True,
	)

	data = []

	for record in checkin_records:
		checkin_datetime = get_datetime(
			record.checkin_time
		)

		data.append(
			{
				"employee_name": (
					record.employee_name
					or record.employee
				),
				"date": checkin_datetime.date(),
				"time": checkin_datetime.strftime(
					"%H:%M:%S"
				),
				"log_type": record.log_type,
			}
		)

	return data