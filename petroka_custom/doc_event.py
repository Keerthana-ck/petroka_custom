import frappe
# import json
from frappe import _
from frappe.utils import add_years, formatdate, add_days, getdate, nowdate

def validate_air_ticket_allowance(doc, method=None):
    air_ticket_expenses = [
        expense
        for expense in (doc.expenses or [])
        if expense.expense_type == "Air Ticket Allowance"
    ]

    if not air_ticket_expenses:
        return

    if not doc.employee:
        frappe.throw(
            _("Employee is required for Air Ticket Allowance.")
        )

    if not doc.custom_date_of_joining:
        frappe.throw(
            _("Date of Joining is required for Air Ticket Allowance.")
        )

    joining_date = getdate(doc.custom_date_of_joining)
    eligibility_date = add_years(joining_date, 1)

    for expense in air_ticket_expenses:
        if not expense.expense_date:
            frappe.throw(
                _("Expense Date is required for Air Ticket Allowance.")
            )

        expense_date = getdate(expense.expense_date)

        if expense_date < eligibility_date:
            frappe.throw(
                _(
                    "Air Ticket Allowance can only be claimed after completing "
                    "one year in the company. The employee becomes eligible on {0}."
                ).format(formatdate(eligibility_date))
            )

def set_last_air_ticket_claim_date(doc, method=None):
    """Set the previous approved Air Ticket Allowance claim date."""

    if not doc.employee:
        return

    # Run only when the current claim contains Air Ticket Allowance
    has_air_ticket_allowance = any(
        row.expense_type == "Air Ticket Allowance"
        for row in doc.expenses
    )

    if not has_air_ticket_allowance:
        return

    claimed_air_ticket_expenses = frappe.get_all(
        "Expense Claim",
        filters=[
            ["Expense Claim", "employee", "=", doc.employee],
            ["Expense Claim", "workflow_state", "=", "Approved"],
            [
                "Expense Claim Detail",
                "expense_type",
                "=",
                "Air Ticket Allowance"
            ]
        ],
        fields=["name", "posting_date"],
        order_by="posting_date desc",
        limit=1
    )

    if not claimed_air_ticket_expenses:
        return

    last_claimed_expense = claimed_air_ticket_expenses[0]

    doc.db_set(
        "custom_last_air_ticket_allowance_claim_date",
        last_claimed_expense.posting_date,
        update_modified=False
    )


def validate_timesheet_date(doc, method=None):
    # Timesheet Manager can create Timesheets for any date
    if "Timesheet Manager" in frappe.get_roles(
        frappe.session.user
    ):
        return

    today = getdate(nowdate())
    yesterday = getdate(add_days(today, -1))

    for row in doc.time_logs:
        if not row.from_time:
            continue

        timesheet_date = getdate(row.from_time)

        # Do not allow future dates
        if timesheet_date > today:
            frappe.throw(
                _(
                    "Row {0}: Future Timesheet entries are not allowed."
                ).format(row.idx)
            )

        # Allow only today and yesterday
        if timesheet_date not in [today, yesterday]:
            frappe.throw(
                _(
                    "Row {0}: Timesheet entries are allowed only "
                    "for today ({1}) or yesterday ({2})."
                ).format(
                    row.idx,
                    frappe.format_value(
                        today,
                        {"fieldtype": "Date"}
                    ),
                    frappe.format_value(
                        yesterday,
                        {"fieldtype": "Date"}
                    )
                )
            )
            

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

def set_hr_manager(doc, method=None):
    """Set the user who moves the document to Approved."""

    if (
        doc.workflow_state == "Approved"
        and doc.has_value_changed("workflow_state")
    ):
        doc.hr_manager = frappe.session.user