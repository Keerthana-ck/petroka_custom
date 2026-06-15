import frappe
import json
from frappe.utils import (
	getdate,
	today,
	add_days,
	flt
)


@frappe.whitelist()
def create_leave_allocation(doc, method=None):
	"""
	Create compensatory off leave allocation
	from approved Work Request task
	"""

	# Validate task
	if doc.task_type != "Work Request":
		return

	if doc.workflow_state != "Approved":
		return

	# Get assigned user
	assigned_users = json.loads(doc._assign or "[]")

	if not assigned_users:
		return

	assigned_user = assigned_users[0]

	# Get employee
	employee = frappe.get_value(
		"Employee",
		{"user_id": assigned_user},
		"name"
	)

	if not employee:
		frappe.msgprint(
			f"No Employee linked with user {assigned_user}"
		)
		return

	# Dates
	if doc.exp_start_date:
		from_date = getdate(doc.exp_start_date)
	else:
		from_date = getdate(today())

	to_date = add_days(from_date, 90)

	# Existing allocation
	allocation_name = frappe.db.exists(
		"Leave Allocation",
		{
			"employee": employee,
			"leave_type": "Compensatory Off",
			"docstatus": 1
		}
	)

	if allocation_name:

		leave_allocation = frappe.get_doc(
			"Leave Allocation",
			allocation_name
		)

		# Prevent duplicate task
		for row in leave_allocation.tasks:

			if row.task == doc.name:
				return

		# Extend allocation date
		if getdate(to_date) > getdate(
			leave_allocation.to_date
		):

			frappe.db.set_value(
				"Leave Allocation",
				leave_allocation.name,
				"to_date",
				to_date,
				update_modified=False
			)

		# Increase available leaves
		leave_allocation.flags.ignore_validate_update_after_submit = True

		leave_allocation.new_leaves_allocated = (
			flt(leave_allocation.new_leaves_allocated) + 1
		)

		leave_allocation.save(
			ignore_permissions=True
		)

		# Insert child row directly
		leave_allocation.append("tasks", {
			"task": doc.name,
			"from_date": from_date,
			"to_date": to_date,
			"expired": 0
		})
		for i, row in enumerate(leave_allocation.tasks, start=1):
			row.idx = i

		leave_allocation.save(ignore_permissions=True)

	else:

		leave_allocation = frappe.new_doc(
			"Leave Allocation"
		)

		leave_allocation.employee = employee
		leave_allocation.leave_type = "Compensatory Off"

		leave_allocation.from_date = from_date
		leave_allocation.to_date = to_date

		leave_allocation.new_leaves_allocated = 1

		leave_allocation.append("tasks", {
			"task": doc.name,
			"from_date": from_date,
			"to_date": to_date,
			"expired": 0
		})

		leave_allocation.insert(
			ignore_permissions=True
		)

		leave_allocation.submit()

	frappe.db.commit()


@frappe.whitelist()
def expire_leave_allocation():
	"""
	Expire compensatory off rows when:
	1. Task expiry date passed
	2. Leave not used
	"""

	leave_allocations = frappe.get_all(
		"Leave Allocation",
		filters={
			"leave_type": "Compensatory Off",
			"docstatus": 1
		},
		pluck="name"
	)

	for allocation_name in leave_allocations:

		leave_allocation = frappe.get_doc(
			"Leave Allocation",
			allocation_name
		)

		if not leave_allocation.tasks:
			continue

		current_new = flt(
			leave_allocation.new_leaves_allocated
		)

		allocation_changed = False

		for row in leave_allocation.tasks:

			# Already expired
			if row.expired:
				continue

			# Invalid dates
			if not row.from_date or not row.to_date:
				continue

			# Still active
			if getdate(row.to_date) > getdate(today()):
				continue

			# Check leave usage
			leave_exists = frappe.db.exists(
				"Leave Application",
				{
					"employee": leave_allocation.employee,
					"leave_type": "Compensatory Off",
					"from_date": row.from_date,
					"to_date": row.to_date,
					"docstatus": 1
				}
			)

			# Leave not used
			if not leave_exists:

				# Reduce available balance
				current_new = max(
					current_new - 1,
					0
				)

				allocation_changed = True

				# IMPORTANT:
				# Create negative leave ledger entry
				# This updates Expired Leaves column
				ledger = frappe.new_doc(
					"Leave Ledger Entry"
				)

				ledger.employee = leave_allocation.employee

				ledger.leave_type = "Compensatory Off"

				ledger.transaction_type = "Leave Allocation"

				ledger.transaction_name = leave_allocation.name

				ledger.leaves = -1

				ledger.from_date = row.from_date
				ledger.to_date = row.to_date

				# IMPORTANT
				ledger.is_expired = 1

				ledger.is_carry_forward = 0

				ledger.insert(ignore_permissions=True)
				ledger.submit()

			# Mark task expired
			frappe.db.set_value(
				"Task List",
				row.name,
				"expired",
				1,
				update_modified=False
			)

		# Update available leaves only
		if allocation_changed:

			leave_allocation.flags.ignore_validate_update_after_submit = True

			leave_allocation.new_leaves_allocated = (
				current_new
			)

			leave_allocation.save(
				ignore_permissions=True
			)

	frappe.db.commit()

@frappe.whitelist()
def validate_bereavement_leave(doc, method=None):
	"""This function validates the total leave days for bereavement leave based on the relation of the employee to the deceased."""

	if doc.leave_type != "Bereavement Leave":
		return

	if doc.custom_relation == "Spouse" and doc.total_leave_days > 5:
		frappe.throw(
			"Bereavement Leave for Spouse cannot exceed 5 days."
		)

	elif doc.custom_relation == "Other Relations" and doc.total_leave_days > 3:
		frappe.throw(
			"Bereavement Leave for Other Relations cannot exceed 3 days."
		)