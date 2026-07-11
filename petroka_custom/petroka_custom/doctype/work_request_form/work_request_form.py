# Copyright (c) 2026, Administrator and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, today

class WorkRequestForm(Document):

	def on_submit(self):
		self.create_leave_allocation()

	def on_cancel(self):
		self.remove_from_leave_allocation()

	def create_leave_allocation(self):
		employee = self.employee

		if not employee:
			frappe.throw(
				"Please select an Employee before submitting the Work Request Form."
			)

		from_date = getdate(self.start_date or today())
		to_date = add_days(from_date, 90)

		allocation_name = frappe.db.exists(
			"Leave Allocation",
			{
				"employee": employee,
				"leave_type": "Compensatory Off",
				"docstatus": 1,
				"from_date": ("<=", from_date),
				"to_date": (">=", from_date),
			},
		)

		if allocation_name:
			self.update_existing_leave_allocation(
				allocation_name=allocation_name,
				from_date=from_date,
				to_date=to_date,
			)
		else:
			self.create_new_leave_allocation(
				employee=employee,
				from_date=from_date,
				to_date=to_date,
			)

	def remove_from_leave_allocation(self):
		"""
		Remove only this Work Request row.

		If other Work Requests remain:
		- Keep the Leave Allocation submitted
		- Reduce allocated leave by one
		- Recalculate allocation dates

		If no Work Requests remain:
		- Cancel the Leave Allocation
		"""

		allocation_names = frappe.get_all(
			"Leave Allocation",
			filters={
				"employee": self.employee,
				"leave_type": "Compensatory Off",
				"docstatus": 1,
			},
			pluck="name",
		)

		for allocation_name in allocation_names:
			leave_allocation = frappe.get_doc(
				"Leave Allocation",
				allocation_name,
			)

			matching_rows = [
				row
				for row in leave_allocation.get(
					"custom_work_order_list",
					[],
				)
				if row.work_request_list == self.name
			]

			if not matching_rows:
				continue

			leave_allocation.flags.ignore_validate_update_after_submit = True
			leave_allocation.flags.ignore_permissions = True

			for row in matching_rows:
				leave_allocation.remove(row)

			remaining_rows = leave_allocation.get(
				"custom_work_order_list",
				[],
			)

			if not remaining_rows:
				# Cancel only when all corresponding Work Requests
				# have been removed/cancelled.
				leave_allocation.flags.ignore_links = True
				leave_allocation.cancel()
				return

			# Reduce the leave allocation only for this Work Request.
			leave_allocation.new_leaves_allocated = max(
				flt(leave_allocation.new_leaves_allocated)
				- len(matching_rows),
				0,
			)

			# Keep Total Leaves Allocated synchronized.
			leave_allocation.total_leaves_allocated = (
				leave_allocation.new_leaves_allocated
			)

			# Recalculate the allocation period using remaining rows.
			valid_from_dates = [
				getdate(row.from_date)
				for row in remaining_rows
				if row.from_date
			]

			valid_to_dates = [
				getdate(row.to_date)
				for row in remaining_rows
				if row.to_date
			]

			if valid_from_dates:
				leave_allocation.from_date = min(
					valid_from_dates
				)

			if valid_to_dates:
				leave_allocation.to_date = max(
					valid_to_dates
				)

			leave_allocation.save(
				ignore_permissions=True
			)

			return

	def update_existing_leave_allocation(
		self,
		allocation_name,
		from_date,
		to_date,
	):
		leave_allocation = frappe.get_doc(
			"Leave Allocation",
			allocation_name,
		)

		# Prevent duplicate allocation for the same Work Request.
		for row in leave_allocation.get(
			"custom_work_order_list",
			[],
		):
			if row.work_request_list == self.name:
				return

		leave_allocation.flags.ignore_validate_update_after_submit = True
		leave_allocation.flags.ignore_permissions = True

		if (
			not leave_allocation.to_date
			or getdate(to_date)
			> getdate(leave_allocation.to_date)
		):
			leave_allocation.to_date = to_date

		if (
			not leave_allocation.from_date
			or getdate(from_date)
			< getdate(leave_allocation.from_date)
		):
			leave_allocation.from_date = from_date

		leave_allocation.new_leaves_allocated = (
			flt(leave_allocation.new_leaves_allocated) + 1
		)

		leave_allocation.total_leaves_allocated = (
			leave_allocation.new_leaves_allocated
		)

		leave_allocation.append(
			"custom_work_order_list",
			{
				"work_request_list": self.name,
				"from_date": from_date,
				"to_date": to_date,
				"expired": 0,
			},
		)

		leave_allocation.save(
			ignore_permissions=True
		)

	def create_new_leave_allocation(
		self,
		employee,
		from_date,
		to_date,
	):
		leave_allocation = frappe.new_doc(
			"Leave Allocation"
		)

		leave_allocation.employee = employee
		leave_allocation.leave_type = "Compensatory Off"
		leave_allocation.from_date = from_date
		leave_allocation.to_date = to_date
		leave_allocation.new_leaves_allocated = 1
		leave_allocation.total_leaves_allocated = 1

		leave_allocation.append(
			"custom_work_order_list",
			{
				"work_request_list": self.name,
				"from_date": from_date,
				"to_date": to_date,
				"expired": 0,
			},
		)

		leave_allocation.insert(
			ignore_permissions=True
		)

		leave_allocation.submit()

@frappe.whitelist()
def expire_leave_allocation():
	"""
	Expire Compensatory Off rows when:

	1. The Work Request expiry date has passed.
	2. The Compensatory Off leave has not been used.
	3. The row has not already been marked as expired.
	"""

	leave_allocations = frappe.get_all(
		"Leave Allocation",
		filters={
			"leave_type": "Compensatory Off",
			"docstatus": 1,
		},
		pluck="name",
	)

	for allocation_name in leave_allocations:
		leave_allocation = frappe.get_doc(
			"Leave Allocation",
			allocation_name,
		)

		if not leave_allocation.custom_work_order_list:
			continue

		current_new = flt(
			leave_allocation.new_leaves_allocated
		)

		allocation_changed = False
		row_updated = False

		for row in leave_allocation.custom_work_order_list:

			# Skip rows that are already expired.
			if row.expired:
				continue

			# Skip rows without proper dates.
			if not row.from_date or not row.to_date:
				continue

			# Skip rows that are still active.
			if getdate(row.to_date) > getdate(today()):
				continue

			# Check whether the Compensatory Off leave was used.
			leave_exists = frappe.db.exists(
				"Leave Application",
				{
					"employee": leave_allocation.employee,
					"leave_type": "Compensatory Off",
					"from_date": row.from_date,
					"to_date": row.to_date,
					"docstatus": 1,
				},
			)

			# If the leave was not used, expire one leave.
			if not leave_exists:

				# Reduce the Leave Allocation quantity.
				current_new = max(
					flt(current_new) - 1,
					0,
				)

				allocation_changed = True

				# Prevent duplicate expiry ledger entries.
				ledger_exists = frappe.db.exists(
					"Leave Ledger Entry",
					{
						"employee": leave_allocation.employee,
						"leave_type": "Compensatory Off",
						"transaction_type": "Leave Allocation",
						"transaction_name": leave_allocation.name,
						"from_date": row.from_date,
						"to_date": row.to_date,
						"leaves": -1,
						"is_expired": 1,
						"docstatus": 1,
					},
				)

				if not ledger_exists:
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

					ledger.is_expired = 1
					ledger.is_carry_forward = 0

					ledger.insert(ignore_permissions=True)
					ledger.submit()

			# Mark the Work Request row as processed/expired.
			row.expired = 1
			row_updated = True

		if allocation_changed or row_updated:
			leave_allocation.flags.ignore_validate_update_after_submit = True

			if allocation_changed:
				leave_allocation.new_leaves_allocated = current_new

			leave_allocation.save(
				ignore_permissions=True
			)

	frappe.db.commit()

	return {
		"status": "success",
		"message": "Compensatory Off expiry completed successfully.",
	}
