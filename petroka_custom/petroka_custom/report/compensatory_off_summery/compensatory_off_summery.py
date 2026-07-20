# Copyright (c) 2026, Administrator and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


CHILD_TABLE_FIELD = "custom_work_order_list"

# Update these two values if your actual child-table
# fieldnames are different.
ALLOCATED_LEAVE_FIELD = "allocated_leave"
EXPIRED_FIELD = "expired"

LEAVE_TYPE = "Compensatory Off"


def execute(filters=None):
	filters = frappe._dict(filters or {})

	validate_filters(filters)

	columns = get_columns()
	data = get_data(filters)
	report_summary = get_report_summary(data)

	return columns, data, None, None, report_summary


def validate_filters(filters):
	if not filters.from_date:
		frappe.throw(_("Please select From Date."))

	if not filters.to_date:
		frappe.throw(_("Please select To Date."))

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(
			_("From Date cannot be after To Date.")
		)


def get_columns():
	return [
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 140,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 180,
		},
		{
			"label": _("Total Allocated Leaves"),
			"fieldname": "total_allocated_leaves",
			"fieldtype": "Float",
			"precision": 2,
			"width": 170,
		},
		{
			"label": _("Expired Leaves"),
			"fieldname": "expired_leaves",
			"fieldtype": "Float",
			"precision": 2,
			"width": 140,
		},
		{
			"label": _("Balance Leave"),
			"fieldname": "balance_leave",
			"fieldtype": "Float",
			"precision": 2,
			"width": 140,
		},
	]


def get_data(filters):
	allocation_filters = {
		"docstatus": 1,
		"leave_type": LEAVE_TYPE,

		# Include allocations overlapping the selected period.
		"from_date": ["<=", filters.to_date],
		"to_date": [">=", filters.from_date],
	}

	if filters.company:
		allocation_filters["company"] = filters.company

	if filters.employee:
		allocation_filters["employee"] = filters.employee

	allocations = frappe.get_list(
		"Leave Allocation",
		filters=allocation_filters,
		fields=[
			"name",
			"employee",
			"company",
		],
		order_by="employee asc",
		limit_page_length=0,
	)

	if not allocations:
		return []

	child_doctype = get_child_doctype()
	validate_child_fields(child_doctype)

	allocation_names = [
		allocation.name
		for allocation in allocations
	]

	child_rows = frappe.get_all(
		child_doctype,
		filters={
			"parent": ["in", allocation_names],
			"parenttype": "Leave Allocation",
			"parentfield": CHILD_TABLE_FIELD,
		},
		fields=[
			"parent",
			ALLOCATED_LEAVE_FIELD,
			EXPIRED_FIELD,
		],
		limit_page_length=0,
	)

	allocation_map = {
		allocation.name: allocation
		for allocation in allocations
	}

	employee_names = get_employee_names(allocations)

	result = {}

	for allocation in allocations:
		key = (
			allocation.employee,
			allocation.company,
		)

		if key not in result:
			result[key] = {
				"employee": allocation.employee,
				"employee_name": employee_names.get(
					allocation.employee,
					allocation.employee,
				),
				"company": allocation.company,
				"total_allocated_leaves": 0,
				"expired_leaves": 0,
				"balance_leave": 0,
			}

	for row in child_rows:
		allocation = allocation_map.get(row.parent)

		if not allocation:
			continue

		key = (
			allocation.employee,
			allocation.company,
		)

		allocated_leave = flt(
			row.get(ALLOCATED_LEAVE_FIELD)
		)

		result[key]["total_allocated_leaves"] += (
			allocated_leave
		)

		if cint(row.get(EXPIRED_FIELD)):
			result[key]["expired_leaves"] += (
				allocated_leave
			)
		else:
			result[key]["balance_leave"] += (
				allocated_leave
			)

	data = list(result.values())

	data.sort(
		key=lambda row: (
			row.get("employee_name") or "",
			row.get("company") or "",
		)
	)

	return data


def get_child_doctype():
	table_field = frappe.get_meta(
		"Leave Allocation"
	).get_field(CHILD_TABLE_FIELD)

	if not table_field:
		frappe.throw(
			_(
				"Child table field {0} was not found "
				"in Leave Allocation."
			).format(
				frappe.bold(CHILD_TABLE_FIELD)
			)
		)

	if not table_field.options:
		frappe.throw(
			_(
				"No Child DocType is configured for {0}."
			).format(
				frappe.bold(CHILD_TABLE_FIELD)
			)
		)

	return table_field.options


def validate_child_fields(child_doctype):
	child_meta = frappe.get_meta(child_doctype)

	missing_fields = []

	if not child_meta.get_field(ALLOCATED_LEAVE_FIELD):
		missing_fields.append(ALLOCATED_LEAVE_FIELD)

	if not child_meta.get_field(EXPIRED_FIELD):
		missing_fields.append(EXPIRED_FIELD)

	if missing_fields:
		frappe.throw(
			_(
				"The following fields were not found "
				"in Child DocType {0}: {1}"
			).format(
				frappe.bold(child_doctype),
				", ".join(missing_fields),
			)
		)


def get_employee_names(allocations):
	employee_ids = list(
		{
			allocation.employee
			for allocation in allocations
			if allocation.employee
		}
	)

	if not employee_ids:
		return {}

	employees = frappe.get_all(
		"Employee",
		filters={
			"name": ["in", employee_ids]
		},
		fields=[
			"name",
			"employee_name",
		],
		limit_page_length=0,
	)

	return {
		employee.name: employee.employee_name
		for employee in employees
	}


def get_report_summary(data):
	total_allocated = sum(
		flt(row.get("total_allocated_leaves"))
		for row in data
	)

	total_expired = sum(
		flt(row.get("expired_leaves"))
		for row in data
	)

	total_balance = sum(
		flt(row.get("balance_leave"))
		for row in data
	)

	return [
		{
			"label": _("Total Allocated"),
			"value": total_allocated,
			"datatype": "Float",
			"indicator": "Blue",
		},
		{
			"label": _("Expired Leaves"),
			"value": total_expired,
			"datatype": "Float",
			"indicator": "Red",
		},
		{
			"label": _("Balance Leave"),
			"value": total_balance,
			"datatype": "Float",
			"indicator": "Green",
		},
	]