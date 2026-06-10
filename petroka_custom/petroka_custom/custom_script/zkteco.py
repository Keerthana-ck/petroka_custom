import frappe
from frappe.utils import now_datetime


@frappe.whitelist()
def enqueue_sync_zkteco_logs():
    print("============")
    """
    Enqueue sync_zkteco_logs to run in the background to prevent timeouts.
    """
    frappe.enqueue(
        method="petroka_custom.petroka_custom.custom_script.zkteco.sync_zkteco_logs",  # Adjust import path as needed
        queue="long",  # or 'default'
        timeout=3600,
        now=False
    )
    frappe.msgprint("✅ Sync has been scheduled. Please check background jobs for status.")

@frappe.whitelist()
def sync_zkteco_logs():
    """
    Sync ZKTeco Check-In Logs to create accurate Employee Check-In and Check-Out entries.
    """
    try:
        # Default shift times as a fallback
        default_shift_start_time = "08:30:00"
        default_shift_end_time = "18:30:00"

        # Fetch ZKTeco Check-In Logs
        zktecho_logs = frappe.get_all(
            "ZKtecho Check-In Logs",
            filters={"time": ["<=", now_datetime()]},  # Fetch all logs until now
            fields=["employee", "time", "log_type"]
        )
       
        if not zktecho_logs:
            frappe.msgprint("No ZKTeco logs available for processing.")
            return

        # Organize logs by employee and date
        logs_by_employee = {}
        for log in zktecho_logs:
            employee = log["employee"]
            log_date = log["time"].date()

            logs_by_employee.setdefault(employee, {}).setdefault(log_date, []).append(log)

        # Process logs for each employee and date
        for employee, logs_by_date in logs_by_employee.items():
            for date, logs in logs_by_date.items():
                # Fetch shift details
                shift_details = get_employee_shift_details(employee, date)
                shift_start_time = shift_details.get("start_time", default_shift_start_time)
                shift_end_time = shift_details.get("end_time", default_shift_end_time)
                shift_type = shift_details.get("shift_type", "Day Shift")

                # Sort logs by time
                logs.sort(key=lambda x: x["time"])

                # Determine Check-IN and Check-OUT
                check_in, check_out = determine_check_in_out(logs, shift_start_time, shift_end_time)

                # Create Employee Check-In entries
                if check_in:
                    create_employee_checkin(employee, check_in["time"], "IN", shift_type)
                if check_out:
                    create_employee_checkin(employee, check_out["time"], "OUT", shift_type)

        frappe.msgprint("ZKTeco logs synced successfully.")

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="ZKTeco Logs Sync Error")
        frappe.throw("An error occurred while syncing ZKTeco logs.")


def get_employee_shift_details(employee, date):
    """
    Fetch shift details for an employee on a specific date from the Shift Assignment document.
    """
    shift_assignment = frappe.db.get_value(
        "Shift Assignment",
        {"employee": employee, "start_date": ["<=", date], "end_date": [">=", date]},
        ["shift_type", "start_date", "end_date"],
        as_dict=True
    )
    if shift_assignment:
        return {
            "shift_type": shift_assignment.get("shift_type"),
            "start_time": shift_assignment.get("start_time").strftime("%H:%M:%S")
            if shift_assignment.get("start_time") else "08:30:00",
            "end_time": shift_assignment.get("end_time").strftime("%H:%M:%S")
            if shift_assignment.get("end_time") else "18:30:00",
        }
    # Default shift if no assignment exists
    return {"shift_type": "Day Shift", "start_time": "08:30:00", "end_time": "18:30:00"}


def determine_check_in_out(logs, shift_start_time, shift_end_time):
    """
    Determine the first Check-In and last Check-Out based on shift times.
    """
    check_in, check_out = None, None

    for log in logs:
        log_time = log["time"].strftime("%H:%M:%S")

        # Determine Check-In
        if not check_in and log_time >= shift_start_time:
            check_in = log
        elif not check_in:  # First log of the day
            check_in = log

    for log in reversed(logs):  # Traverse from the last log
        log_time = log["time"].strftime("%H:%M:%S")

        # Determine Check-Out
        if not check_out and log_time >= shift_end_time:
            check_out = log
        elif not check_out:  # Last log of the day
            check_out = log

    return check_in, check_out


def create_employee_checkin(employee, time, log_type, shift_type):
    """
    Create Employee Check-In entry if it doesn't already exist.
    """

    # Yahan apni actual ZKTeco machine / branch location ki latitude longitude daalo
    DEFAULT_LATITUDE = 13.043
    DEFAULT_LONGITUDE = 80.274

    try:
        exists = frappe.db.exists(
            "Employee Checkin",
            {
                "employee": employee,
                "time": time
            }
        )

        if exists:
            frappe.log_error(
                f"Duplicate skipped: {employee} | {time} | {log_type}",
                "ZKTeco Employee Checkin Duplicate"
            )
            return

        doc_data = {
            "doctype": "Employee Checkin",
            "employee": employee,
            "time": time,
            "log_type": log_type,

            # Required because HRMS shift location validation is enabled
            "latitude": DEFAULT_LATITUDE,
            "longitude": DEFAULT_LONGITUDE,
        }

        # Shift only add karo agar valid Shift Type hai
        if shift_type and frappe.db.exists("Shift Type", shift_type):
            doc_data["shift"] = shift_type

        doc = frappe.get_doc(doc_data)
        doc.insert(ignore_permissions=True)

        frappe.log_error(
            f"Employee Checkin created: {doc.name} | {employee} | {time} | {log_type}",
            "ZKTeco Employee Checkin Created"
        )

    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title="Employee Check-In Creation Error"
        )
        frappe.throw(f"Failed to create Employee Check-In: {str(e)}")

# def create_employee_checkin(employee, time, log_type, shift_type):
#     """
#     Create Employee Check-In entry if it doesn't already exist.
#     """

#     try:
#         exists = frappe.db.exists(
#             "Employee Checkin",
#             {
#                 "employee": employee,
#                 "time": time
#             }
#         )

#         if exists:
#             return

#         latitude = None
#         longitude = None

#         # Get coordinates from Shift Location
#         try:
#             if shift_type and frappe.db.exists("Shift Type", shift_type):

#                 shift_doc = frappe.get_doc("Shift Type", shift_type)

#                 shift_location = shift_doc.get("shift_location")

#                 if shift_location and frappe.db.exists("Shift Location", shift_location):

#                     location_doc = frappe.get_doc(
#                         "Shift Location",
#                         shift_location
#                     )

#                     latitude = location_doc.get("latitude")
#                     longitude = location_doc.get("longitude")

#         except Exception:
#             frappe.log_error(
#                 frappe.get_traceback(),
#                 f"Unable to fetch Shift Location - {employee}"
#             )

#         doc_data = {
#             "doctype": "Employee Checkin",
#             "employee": employee,
#             "time": time,
#             "log_type": log_type,
#             "latitude": latitude,
#             "longitude": longitude,
#         }

#         if shift_type and frappe.db.exists("Shift Type", shift_type):
#             doc_data["shift"] = shift_type

#         doc = frappe.get_doc(doc_data)
#         doc.insert(ignore_permissions=True)

#         frappe.db.commit()

#         frappe.logger().info(
#             f"Employee Checkin Created: {employee} | {time} | {log_type}"
#         )

#     except Exception:
#         frappe.log_error(
#             message=f"""
#         Employee: {employee}
#         Shift: {shift_type}
#         Time: {time}
#         Log Type: {log_type}

#         {frappe.get_traceback()}
#         """,
#                     title="Employee Check-In Creation Error"
#                 )