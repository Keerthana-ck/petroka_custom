import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from hrms.hr.doctype.leave_application.leave_application import (
	InsufficientLeaveBalanceError,
	LeaveApplication,
	get_leave_balance_on,
	get_number_of_leave_days,
	is_lwp,
)


class CustomLeaveApplication(LeaveApplication):
	def validate_balance_leaves(self):
		precision = cint(frappe.db.get_single_value("System Settings", "float_precision")) or 2

		if not (self.employee and self.leave_type and self.from_date and self.to_date):
			return

		self.total_leave_days = get_number_of_leave_days(
			self.employee,
			self.leave_type,
			self.from_date,
			self.to_date,
			self.half_day,
			self.half_day_date,
		)

		if self.total_leave_days <= 0:
			frappe.throw(
				_("The day(s) on which you are applying for leave are holidays. You need not apply for leave.")
			)

		if is_lwp(self.leave_type):
			self.set_future_leave_fields(0, 0)
			return

		annual_allocation = flt(self.get_annual_allocation(), precision)
		if not annual_allocation:
			super().validate_balance_leaves()
			self.set_future_leave_fields(0, 0)
			return

		current_balance = flt(self.get_current_leave_balance(), precision)
		future_earned_leave = flt(self.get_future_earned_leave(), precision)
		total_eligible_leave = flt(current_balance + future_earned_leave, precision)

		self.set_future_leave_fields(future_earned_leave, total_eligible_leave)

		if self.status != "Rejected" and flt(self.total_leave_days, precision) > total_eligible_leave:
			frappe.throw(
				_(
					"Insufficient Future Leave Balance.<br><br>"
					"Current Balance: <b>{0}</b><br>"
					"Future Earned Leave: <b>{1}</b><br>"
					"Total Eligible Leave: <b>{2}</b><br>"
					"Requested Leave: <b>{3}</b><br><br>"
					"Your requested leave exceeds the total eligible future leave balance, so the leave application cannot be saved."
				).format(
					flt(current_balance, precision),
					flt(future_earned_leave, precision),
					flt(total_eligible_leave, precision),
					flt(self.total_leave_days, precision),
				),
				exc=InsufficientLeaveBalanceError,
				title=_("Insufficient Balance"),
			)

	def get_current_leave_balance(self):
		application_date = self.get_application_date()
		return get_leave_balance_on(
			self.employee,
			self.leave_type,
			application_date,
			consider_all_leaves_in_the_allocation_period=True,
		)

	def get_future_earned_leave(self):
		if not self.get_annual_allocation():
			return 0

		months = self.get_months_until_leave()
		return 2 * months

	def get_annual_allocation(self):
		allocation = frappe.db.get_value(
			"Leave Allocation",
			{
				"employee": self.employee,
				"leave_type": self.leave_type,
				"docstatus": 1,
				"from_date": ["<=", self.from_date],
				"to_date": [">=", self.get_application_date()],
			},
			["total_leaves_allocated"],
			order_by="from_date desc",
			as_dict=True,
		)

		return flt(allocation.total_leaves_allocated) if allocation else 0

	def get_months_until_leave(self):
		application_date = getdate(self.get_application_date())
		leave_end_date = getdate(self.to_date)
		months = (leave_end_date.year - application_date.year) * 12 + (
			leave_end_date.month - application_date.month
		)

		return max(months, 0)

	def get_application_date(self):
		return self.posting_date or today()

	def set_future_leave_fields(self, future_earned_leave, total_eligible_leave):
		if self.meta.has_field("future_earned_leave"):
			self.future_earned_leave = future_earned_leave

		if self.meta.has_field("total_eligible_leave"):
			self.total_eligible_leave = total_eligible_leave
