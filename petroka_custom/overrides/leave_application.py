import calendar
import math

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
	def round_down_half(self, value):
		return math.floor(flt(value) * 2) / 2
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
		# future_earned_leave = flt(self.get_future_earned_leave(), precision)
		# total_eligible_leave = flt(current_balance + future_earned_leave, precision)
		future_earned_leave = self.round_down_half(
			flt(self.get_future_earned_leave(), precision)
		)

		total_eligible_leave = self.round_down_half(
			flt(current_balance + future_earned_leave, precision)
		)
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
		allocation = self.get_leave_allocation()
		if not allocation:
			return 0

		monthly_accrual = flt(allocation.total_leaves_allocated) / 12
		months = self.get_future_accrual_months(allocation)
		return monthly_accrual * months

	def get_annual_allocation(self):
		allocation = self.get_leave_allocation()
		return flt(allocation.total_leaves_allocated) if allocation else 0

	def get_leave_allocation(self):
		allocation = frappe.db.get_value(
			"Leave Allocation",
			{
				"employee": self.employee,
				"leave_type": self.leave_type,
				"docstatus": 1,
				"from_date": ["<=", self.from_date],
				"to_date": [">=", self.get_application_date()],
			},
			["name", "from_date", "to_date", "total_leaves_allocated"],
			order_by="from_date desc",
			as_dict=True,
		)

		return allocation

	def get_future_accrual_months(self, allocation):
		application_date = getdate(self.get_application_date())
		leave_end_date = getdate(self.to_date)
		allocation_from_date = getdate(allocation.from_date)
		allocation_to_date = getdate(allocation.to_date)
		date_of_joining = self.get_employee_date_of_joining()
		if not date_of_joining:
			return 0

		date_of_joining = getdate(date_of_joining)
		accrual_start_date = max(
			self.get_month_start(application_date),
			allocation_from_date,
			date_of_joining,
		)
		accrual_end_date = min(leave_end_date, allocation_to_date)

		if accrual_end_date < accrual_start_date:
			return 0

		return self.get_monthly_doj_accrual_count(
			accrual_start_date,
			accrual_end_date,
			date_of_joining,
		)

	def get_monthly_doj_accrual_count(self, accrual_start_date, accrual_end_date, date_of_joining):
		months = 0
		year = accrual_start_date.year
		month = accrual_start_date.month
		accrual_day = date_of_joining.day

		while (year, month) <= (accrual_end_date.year, accrual_end_date.month):
			accrual_date = self.get_monthly_accrual_date(year, month, accrual_day)

			if (
				accrual_date >= accrual_start_date
				and accrual_date <= accrual_end_date
				and accrual_date >= date_of_joining
			):
				months += 1

			month += 1
			if month > 12:
				month = 1
				year += 1

		return months

	def get_monthly_accrual_date(self, year, month, accrual_day):
		last_day = calendar.monthrange(year, month)[1]
		return getdate(f"{year}-{month:02d}-{min(accrual_day, last_day):02d}")

	def get_month_start(self, date):
		date = getdate(date)
		return getdate(f"{date.year}-{date.month:02d}-01")

	def get_employee_date_of_joining(self):
		return frappe.db.get_value("Employee", self.employee, "date_of_joining")

	def get_application_date(self):
		return self.posting_date or today()

	def set_future_leave_fields(self, future_earned_leave, total_eligible_leave):
		if self.meta.has_field("future_earned_leave"):
			self.future_earned_leave = future_earned_leave

		if self.meta.has_field("total_eligible_leave"):
			self.total_eligible_leave = total_eligible_leave
