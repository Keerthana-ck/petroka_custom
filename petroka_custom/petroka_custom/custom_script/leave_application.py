# import frappe
# from frappe.utils import getdate, today, flt

# from hrms.hr.doctype.leave_application.leave_application import (
#     get_leave_balance_on,
# )


# def validate_future_leave_balance(doc, method=None):
#     print("jjjjjjjjjjjjjjjjjjj++++++++++++++")

#     if not doc.employee or not doc.leave_type or not doc.from_date:
#         return

#     # Get Leave Type
#     leave_type = frappe.get_doc("Leave Type", doc.leave_type)

#     # Only for Earned Leave
#     if not leave_type.is_earned_leave:
#         return

#     # Current Leave Balance
#     current_balance = flt(
#         get_leave_balance_on(
#             doc.employee,
#             doc.leave_type,
#             today(),
#             consider_all_leaves_in_the_allocation_period=True,
#         )
#     )

#     # Leave Allocation
#     allocation = frappe.db.get_value(
#         "Leave Allocation",
#         {
#             "employee": doc.employee,
#             "leave_type": doc.leave_type,
#             "docstatus": 1,
#         },
#         [
#             "total_leaves_allocated",
#         ],
#         as_dict=True,
#     )

#     if not allocation:
#         return

#     annual_allocation = flt(allocation.total_leaves_allocated)

#     # Monthly accrual
#     monthly_accrual = annual_allocation / 12

#     current_date = getdate(today())
#     leave_date = getdate(doc.from_date)

#     # Month difference
#     months = (
#         (leave_date.year - current_date.year) * 12
#         + (leave_date.month - current_date.month)
#     )

#     if months < 0:
#         months = 0

#     # Future leave earning
#     future_earned_leave = flt(monthly_accrual * months)

#     # Total eligible leave
#     total_eligible_leave = flt(
#         current_balance + future_earned_leave
#     )

#     # Prevent exceeding yearly allocation
#     if total_eligible_leave > annual_allocation:
#         total_eligible_leave = annual_allocation

#     # Set custom fields
#     doc.future_earned_leave = future_earned_leave
#     doc.total_eligible_leave = total_eligible_leave

#     requested_leave = flt(doc.total_leave_days)

#     # Custom Validation
#     if requested_leave > total_eligible_leave:

#         frappe.throw(
#             f"""
#             Insufficient Future Leave Balance.<br><br>

#             Current Balance: <b>{current_balance}</b><br>
#             Future Earned Leave: <b>{future_earned_leave}</b><br>
#             Total Eligible Leave: <b>{total_eligible_leave}</b><br>
#             Requested Leave: <b>{requested_leave}</b><br><br>
#             Your requested leave exceeds the total eligible future leave balance, so the leave application cannot be saved.
#             """
#         )


from frappe.utils import getdate, today
import frappe


def validate_future_draft_leave(doc, method=None):

    # Current leave future date ke liye honi chahiye
    if getdate(doc.from_date) <= getdate(today()):
        return

    # Existing future draft leave check
    existing_leave = frappe.db.get_value(
        "Leave Application",
        {
            "employee": doc.employee,
            "docstatus": 0,
            "name": ["!=", doc.name],
            "from_date": [">", today()]
        },
        ["name", "from_date", "to_date"],
        as_dict=True
    )

    if existing_leave:

        leave_link = frappe.utils.get_link_to_form(
            "Leave Application",
            existing_leave.name
        )

        frappe.throw(
            f"""
            You already have a future leave application in Draft status.<br><br>

            Existing Draft Leave: {leave_link}<br>
            Leave Period: <b>{existing_leave.from_date}</b> to <b>{existing_leave.to_date}</b><br><br>

            Please contact your manager or leave approver to review and submit/cancel the existing leave application before applying for another future leave.
            """
        )