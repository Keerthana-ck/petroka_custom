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


# from frappe.utils import today, add_days

# from frappe.utils import today, now_datetime

# @frappe.whitelist()
# def sync_morning_checkins():
#     logger = frappe.logger("morning_checkins")

#     current = now_datetime()

#     # Run only between 08:30 AM and 11:00 AM
#     if not (
#         (current.hour == 8 and current.minute >= 30)
#         or (current.hour == 9)
#         or (current.hour == 10)
#         or (current.hour == 11 and current.minute == 0)
#     ):
#         logger.info(f"Skipped execution at {current}")
#         return

#     logger.info("sync_morning_checkins started")

#     process_date = today()
#     logger.info(f"Process date: {process_date}")

#     employees = frappe.db.sql("""
#         SELECT DISTINCT employee
#         FROM `tabZKtecho Check-In Logs`
#         WHERE DATE(time)=%s
#     """, process_date, as_dict=True)

#     logger.info(f"Total employees found: {len(employees)}")

#     for row in employees:
#         employee = row.employee
#         logger.info(f"Processing employee: {employee}")

#         in_exists = frappe.db.sql("""
#             SELECT name
#             FROM `tabEmployee Checkin`
#             WHERE employee=%s
#             AND log_type='IN'
#             AND DATE(time)=%s
#             LIMIT 1
#         """, (employee, process_date))

#         if in_exists:
#             logger.info(f"IN already exists for {employee}, skipping")
#             continue

#         first_log = frappe.db.sql("""
#             SELECT time
#             FROM `tabZKtecho Check-In Logs`
#             WHERE employee=%s
#             AND DATE(time)=%s
#             ORDER BY time ASC
#             LIMIT 1
#         """, (employee, process_date), as_dict=True)

#         if not first_log:
#             logger.info(f"No logs found for {employee}")
#             continue

#         logger.info(f"Creating IN check-in for {employee} at {first_log[0].time}")

#         try:
#             create_employee_checkin(
#                 employee,
#                 first_log[0].time,
#                 "IN",
#                 None
#             )
#             logger.info(f"Successfully created IN check-in for {employee}")

#         except Exception:
#             frappe.log_error(
#                 title=f"Morning Check-in Sync Failed - {employee}",
#                 message=frappe.get_traceback()
#             )
#             logger.error(f"Failed to create check-in for {employee}")

#     frappe.db.commit()
#     logger.info("sync_morning_checkins completed successfully")

from frappe.utils import today, add_days

from frappe.utils import today, now_datetime
from datetime import time

@frappe.whitelist()
def sync_morning_checkins():
    logger = frappe.logger("morning_checkins")

    current = now_datetime()

    # Debug Logs
    logger.info("=" * 60)
    logger.info(f"Current Server Datetime : {current}")
    logger.info(f"Current Time           : {current.time()}")
    logger.info("=" * 60)

    # Allow only between 08:30:00 and 11:00:00
    start_time = time(9, 0, 0)
    end_time = time(11, 30, 0)

    if not (start_time <= current.time() <= end_time):
        logger.info(f"Skipped execution. Current time {current.time()} is outside allowed range.")
        return

    logger.info("sync_morning_checkins started")

    process_date = today()

    employees = frappe.db.sql("""
        SELECT DISTINCT employee
        FROM `tabZKtecho Check-In Logs`
        WHERE DATE(time)=%s
    """, process_date, as_dict=True)

    logger.info(f"Total employees found: {len(employees)}")

    for row in employees:
        employee = row.employee

        logger.info(f"Processing Employee: {employee}")

        # Check if IN already exists
        in_exists = frappe.db.exists(
            "Employee Checkin",
            {
                "employee": employee,
                "log_type": "IN",
                "time": ["between", [f"{process_date} 00:00:00", f"{process_date} 23:59:59"]]
            }
        )

        if in_exists:
            logger.info(f"IN already exists for {employee}")
            continue

        # Get first log of the day
        first_log = frappe.db.sql("""
            SELECT time
            FROM `tabZKtecho Check-In Logs`
            WHERE employee=%s
            AND DATE(time)=%s
            ORDER BY time ASC
            LIMIT 1
        """, (employee, process_date), as_dict=True)

        if not first_log:
            logger.info(f"No logs found for {employee}")
            continue

        logger.info(f"Creating IN for {employee} at {first_log[0].time}")

        try:
            create_employee_checkin(
                employee=employee,
                time=first_log[0].time,
                log_type="IN",
                shift_type=None
            )

            logger.info(f"Successfully created IN for {employee}")

        except Exception:
            logger.error(frappe.get_traceback())
            frappe.log_error(
                title=f"Morning Check-in Sync Failed - {employee}",
                message=frappe.get_traceback()
            )

    frappe.db.commit()

    logger.info("sync_morning_checkins completed successfully")




# @frappe.whitelist()
# def sync_night_checkouts():
#     print("hhhhhhhhhhhhhhhhhhhhhhhhhhh")

#     process_date = add_days(today(), -1)

#     employees = frappe.db.sql("""
#         SELECT DISTINCT employee
#         FROM `tabZKtecho Check-In Logs`
#         WHERE DATE(time)=%s
#     """, process_date, as_dict=True)

#     for row in employees:

#         employee = row.employee

#         logs = frappe.db.sql("""
#             SELECT time
#             FROM `tabZKtecho Check-In Logs`
#             WHERE employee=%s
#             AND DATE(time)=%s
#             ORDER BY time ASC
#         """, (employee, process_date), as_dict=True)

#         if not logs:
#             continue

#         first_log = logs[0].time
#         last_log = logs[-1].time

#         in_exists = frappe.db.sql("""
#             SELECT name
#             FROM `tabEmployee Checkin`
#             WHERE employee=%s
#             AND log_type='IN'
#             AND DATE(time)=%s
#             LIMIT 1
#         """, (employee, process_date))

#         out_exists = frappe.db.sql("""
#             SELECT name
#             FROM `tabEmployee Checkin`
#             WHERE employee=%s
#             AND log_type='OUT'
#             AND DATE(time)=%s
#             LIMIT 1
#         """, (employee, process_date))

#         # Morning me IN ban gaya tha
#         if in_exists:

#             if not out_exists and first_log != last_log:

#                 create_employee_checkin(
#                     employee,
#                     last_log,
#                     "OUT",
#                     None
#                 )

#         # Morning me IN nahi bana
#         else:

#             create_employee_checkin(
#                 employee,
#                 first_log,
#                 "IN",
#                 None
#             )

#             if first_log != last_log:

#                 create_employee_checkin(
#                     employee,
#                     last_log,
#                     "OUT",
#                     None
#                 )

#     frappe.db.commit()