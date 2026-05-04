import json
import frappe
from frappe.utils import today
from frappe.utils import getdate, today, flt, add_days


@frappe.whitelist()
def create_leave_allocation(doc, method=None):
    """This function is triggered on the validate event of a Task document. It checks if the task is of type "Work Request" and is approved."""

    if doc.task_type == "Work Request" and doc.workflow_state == "Approved":

        assigned_users = json.loads(doc._assign or "[]")

        if not assigned_users:
            return

        assigned_user = assigned_users[0]

        employee = frappe.get_value(
            "Employee",
            {"user_id": assigned_user},
            "name"
        )

        if not employee:
            return

        allocation_name = frappe.db.exists(
            "Leave Allocation",
            {
                "employee": employee,
                "from_date": ["<=", doc.exp_start_date],
                "to_date": [">=", doc.exp_start_date],
                "docstatus": 1,
                "leave_type": "Compensatory Off"
            },
        )

        task_to_date = add_days(doc.exp_start_date, 90)

        if allocation_name:

            leave_allocation = frappe.get_doc(
                "Leave Allocation",
                allocation_name
            )

            if getdate(task_to_date) > getdate(leave_allocation.to_date):
                leave_allocation.db_set(
                    "to_date",
                    task_to_date,
                    update_modified=False
                )

            leave_allocation.db_set(
                "new_leaves_allocated",
                (leave_allocation.new_leaves_allocated or 0) + 1,
                update_modified=False
            )

            leave_allocation.db_set(
                "total_leaves_allocated",
                (leave_allocation.total_leaves_allocated or 0) + 1,
                update_modified=False
            )

            # Insert child row directly
            frappe.get_doc({
                "doctype": "Task List",
                "parent": leave_allocation.name,
                "parenttype": "Leave Allocation",
                "parentfield": "tasks",
                "task": doc.name,
                "from_date": doc.exp_start_date,
                "to_date": task_to_date
            }).insert(ignore_permissions=True)

        else:
            leave_allocation = frappe.new_doc("Leave Allocation")
            leave_allocation.employee = employee
            leave_allocation.leave_type = "Compensatory Off"
            leave_allocation.from_date = doc.exp_start_date
            leave_allocation.to_date = task_to_date
            leave_allocation.new_leaves_allocated = 1
            leave_allocation.total_leaves_allocated = 1

            leave_allocation.append("tasks", {
                "task": doc.name,
                "from_date": doc.exp_start_date,
                "to_date": task_to_date
            })

            leave_allocation.insert(ignore_permissions=True)
            leave_allocation.submit()


@frappe.whitelist()
def expire_leave_allocation():
    """
    Expire compensatory off rows when:
    1. Task row to_date is today or passed
    2. No Leave Application exists for that period
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

        allocation_updated = False

        for row in leave_allocation.tasks:

            # Skip already expired rows
            if row.expired:
                continue

            # Skip if no dates
            if not row.from_date or not row.to_date:
                continue

            # Check expiry date
            if getdate(row.to_date) > getdate(today()):
                continue

            # Check if leave application exists
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

            # If leave not used -> reduce allocation
            if not leave_exists:

                current_new = flt(
                    leave_allocation.new_leaves_allocated
                )

                current_total = flt(
                    leave_allocation.total_leaves_allocated
                )

                leave_allocation.db_set(
                    "new_leaves_allocated",
                    max(current_new - 1, 0),
                    update_modified=False
                )

                leave_allocation.db_set(
                    "total_leaves_allocated",
                    max(current_total - 1, 0),
                    update_modified=False
                )

            # Mark row as expired
            row.expired = 1
            allocation_updated = True

        # Save child table updates
        if allocation_updated:
            leave_allocation.save(ignore_permissions=True)

    frappe.db.commit()

        