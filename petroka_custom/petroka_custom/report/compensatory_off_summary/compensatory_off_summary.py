import frappe
from frappe import _
from frappe.utils import flt, getdate


LEAVE_TYPE = "Compensatory Off"
CHILD_TABLE_FIELD = "custom_work_order_list"

ROW_FROM_DATE_FIELD = "from_date"
ROW_TO_DATE_FIELD = "to_date"
EXPIRED_FIELD = "expired"


def execute(filters=None):
	filters = frappe._dict(filters or {})

	validate_filters(filters)

	columns = get_columns()
	data = get_data(filters)
	

	return columns, data, None, None, None


def validate_filters(filters):
	if not filters.from_date:
		frappe.throw(_("Please select From Date."))

	if not filters.to_date:
		frappe.throw(_("Please select To Date."))

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(
			_("From Date cannot be greater than To Date.")
		)


def get_columns():
	return [
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 190,
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 250,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 300,
			"hidden": 1
		},
		{
			"label": _("Total Allocated Leaves"),
			"fieldname": "total_allocated_leaves",
			"fieldtype": "Float",
			"precision": 2,
			"width": 180,
		},
		{
			"label": _("Expired Leaves"),
			"fieldname": "expired_leaves",
			"fieldtype": "Float",
			"precision": 2,
			"width": 180,
		},
		{
			"label": _("Leave Taken"),
			"fieldname": "leave_taken",
			"fieldtype": "Float",
			"precision": 2,
			"width": 150,
		},
		{
			"label": _("Balance Leave"),
			"fieldname": "balance_leave",
			"fieldtype": "Float",
			"precision": 2,
			"width": 180,
		},
	]


def get_data(filters):
	child_doctype = get_child_doctype()

	conditions = [
		"la.docstatus = 1",
		"la.leave_type = %(leave_type)s",
		f"child.`{ROW_FROM_DATE_FIELD}` <= %(to_date)s",
		f"child.`{ROW_TO_DATE_FIELD}` >= %(from_date)s",
	]

	values = {
		"leave_type": LEAVE_TYPE,
		"from_date": filters.from_date,
		"to_date": filters.to_date,
		"child_table_field": CHILD_TABLE_FIELD,
	}

	if filters.company:
		conditions.append(
			"employee.company = %(company)s"
		)
		values["company"] = filters.company

	if filters.employee:
		conditions.append(
			"la.employee = %(employee)s"
		)
		values["employee"] = filters.employee

	data = frappe.db.sql(
		f"""
			SELECT
				la.employee AS employee,
				employee.employee_name AS employee_name,
				employee.company AS company,

				COUNT(child.name)
					AS total_allocated_leaves,

				SUM(
					CASE
						WHEN IFNULL(
							child.`{EXPIRED_FIELD}`,
							0
						) = 1
						THEN 1
						ELSE 0
					END
				) AS expired_leaves,

				IFNULL(
					MAX(leave_usage.leave_taken),
					0
				) AS leave_taken,

				SUM(
					CASE
						WHEN IFNULL(
							child.`{EXPIRED_FIELD}`,
							0
						) = 0
						THEN 1
						ELSE 0
					END
				) AS balance_leave

			FROM `tabLeave Allocation` AS la

			INNER JOIN `tab{child_doctype}` AS child
				ON child.parent = la.name
				AND child.parenttype = 'Leave Allocation'
				AND child.parentfield = %(child_table_field)s

			LEFT JOIN `tabEmployee` AS employee
				ON employee.name = la.employee

			LEFT JOIN (
				SELECT
					leave_application.employee,
					SUM(
						IFNULL(
							leave_application.total_leave_days,
							0
						)
					) AS leave_taken

				FROM `tabLeave Application`
					AS leave_application

				WHERE
					leave_application.docstatus = 1
					AND leave_application.leave_type
						= %(leave_type)s
					AND leave_application.from_date
						<= %(to_date)s
					AND leave_application.to_date
						>= %(from_date)s

				GROUP BY
					leave_application.employee
			) AS leave_usage
				ON leave_usage.employee = la.employee

			WHERE {" AND ".join(conditions)}

			GROUP BY
				la.employee,
				employee.employee_name,
				employee.company

			ORDER BY
				employee.employee_name ASC
		""",
		values,
		as_dict=True,
	)

	for row in data:
		row.total_allocated_leaves = flt(
			row.total_allocated_leaves
		)

		row.expired_leaves = flt(
			row.expired_leaves
		)

		row.leave_taken = flt(
			row.leave_taken
		)

		row.balance_leave = flt(
			row.balance_leave
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


