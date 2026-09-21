import frappe
from frappe.utils import add_days, now_datetime


def cleanup_old_logs():
    batch_size = 700
    cutoff_date = add_days(now_datetime(), -10)

    # ---------------------------------
    # Error Log - only older than 30 days
    # ---------------------------------
    error_logs = frappe.get_all(
        "Error Log",
        filters={
            "creation": ("<", cutoff_date)
        },
        pluck="name",
        limit_page_length=batch_size
    )

    for name in error_logs:
        frappe.delete_doc(
            "Error Log",
            name,
            ignore_permissions=True
        )

    # ---------------------------------
    # Deleted Document
    # Only records where deleted_doctype = Error Log
    # No date condition
    # ---------------------------------
    deleted_docs = frappe.get_all(
        "Deleted Document",
        filters={
            "deleted_doctype": "Error Log"
        },
        pluck="name",
        limit_page_length=batch_size
    )

    for name in deleted_docs:
        frappe.delete_doc(
            "Deleted Document",
            name,
            ignore_permissions=True
        )

    frappe.db.commit()

    return {
        "error_logs_deleted": len(error_logs),
        "deleted_document_error_logs_deleted": len(deleted_docs)
    }