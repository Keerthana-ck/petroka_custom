import frappe
import requests

from time import sleep
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from frappe.utils import now_datetime, add_to_date



# ===================latest
class ZKtechoCheckInLogs(Document):
    pass


@frappe.whitelist()
def enqueue_fetch_and_process_data():
    """
    Enqueue the data fetching task as a background job.
    """

    enqueue(
        "petroka_custom.petroka_custom.doctype.zktecho_check_in_logs.zktecho_check_in_logs.fetch_and_process_data",
        queue="long",
        timeout=3600,
        now=False
    )

    frappe.msgprint("✅ Background job has been enqueued.")


def fetch_and_process_data():
    """
    Fetch transactions from Petroka BioTime API and insert into
    ZKtecho Check-In Logs DocType.

    New Logic:
    - Each Employee will be synced separately by attendance_device_id.
    - For each Employee, start_time = that Employee's latest saved punch time - 10 minutes.
    - If Employee has no saved logs, start_time = INITIAL_START_TIME.
    """

    base_url = "http://petroka.fortiddns.com:8081/iclock/api/transactions/"

    # First-time sync start date.
    # Agar old 2024 data bhi chahiye to isko "2024-01-01 00:00:00" kar do.
    INITIAL_START_TIME = "2026-01-01 00:00:00"

    end_time = now_datetime().strftime("%Y-%m-%d %H:%M:%S")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",

        # Yahan fresh Bearer token lagao.
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwNjQ2MjY1LCJpYXQiOjE3ODA1NTk4NjUsImp0aSI6ImQzODFjMzkwYmVlNzRiZjQ5MzQ4ZjNlMmFmMmM3Y2NiIiwidXNlcl9pZCI6MX0.dex_DhWF33f0hYu2vU5VptGNAmA6BzY44ejyOoFafvs"
    }

    employees = frappe.get_all(
        "Employee",
        filters=[
            ["attendance_device_id", "is", "set"],
            ["attendance_device_id", "!=", ""],
        ],
        fields=["name", "employee_name", "attendance_device_id"],
        order_by="name asc"
    )

    if not employees:
        frappe.log_error(
            "No Employee found with attendance_device_id.",
            "Petroka ZKTeco No Employees To Sync"
        )
        print("⚠️ No Employee found with attendance_device_id.")
        return

    total_inserted = 0
    total_skipped = 0
    total_failed = 0

    frappe.log_error(
        f"""
        ZKTeco Employee Wise Sync Started

        Employees:
        {len(employees)}

        End Time:
        {end_time}
        """,
        "Petroka ZKTeco Sync Started"
    )

    for emp in employees:
        employee = emp.name
        employee_name = emp.employee_name
        device_id = str(emp.attendance_device_id or "").strip()

        if not device_id:
            continue

        try:
            result = sync_single_employee(
                base_url=base_url,
                headers=headers,
                employee=employee,
                employee_name=employee_name,
                device_id=device_id,
                initial_start_time=INITIAL_START_TIME,
                end_time=end_time
            )

            total_inserted += result.get("inserted", 0)
            total_skipped += result.get("skipped", 0)

        except Exception:
            total_failed += 1
            frappe.db.rollback()
            frappe.log_error(
                frappe.get_traceback(),
                f"Petroka ZKTeco Employee Sync Failed - {employee}"
            )

    frappe.log_error(
        f"""
        ZKTeco Employee Wise Sync Finished

        Employees:
        {len(employees)}

        Total Inserted:
        {total_inserted}

        Total Skipped:
        {total_skipped}

        Total Failed Employees:
        {total_failed}

        End Time:
        {end_time}
        """,
        "Petroka ZKTeco Sync Finished"
    )


def sync_single_employee(
    base_url,
    headers,
    employee,
    employee_name,
    device_id,
    initial_start_time,
    end_time
):
    """
    Sync one employee based on that employee's own latest punch time.
    """

    last_time = frappe.db.sql(
        """
        SELECT MAX(`time`)
        FROM `tabZKtecho Check-In Logs`
        WHERE employee = %s
        """,
        (employee,)
    )[0][0]

    if last_time:
        start_time = add_to_date(
            last_time,
            minutes=-10
        ).strftime("%Y-%m-%d %H:%M:%S")
    else:
        start_time = initial_start_time

    page = 1
    inserted_count = 0
    skipped_count = 0

    frappe.log_error(
        f"""
        Employee Sync Started

        Employee:
        {employee}

        Employee Name:
        {employee_name}

        Device ID:
        {device_id}

        Start Time:
        {start_time}

        End Time:
        {end_time}
        """,
        "Petroka ZKTeco Employee Sync Started"
    )

    while True:
        params = {
            "page": page,
            "page_size": 1000,
            "start_time": start_time,
            "end_time": end_time,

            # Important: API ko employee wise filter karne ke liye.
            "emp_code": device_id,
        }

        response = requests.get(
            base_url,
            headers=headers,
            params=params,
            timeout=60,
            verify=False
        )

        if response.status_code != 200:
            frappe.log_error(
                f"""
                Failed to fetch employee transactions

                Employee:
                {employee}

                Device ID:
                {device_id}

                Page:
                {page}

                Status Code:
                {response.status_code}

                URL:
                {response.url}

                Response:
                {response.text[:3000]}
                """,
                "Petroka ZKTeco API Error"
            )

            print(f"❌ Failed: {employee} | Device ID: {device_id} | Page: {page}")
            break

        try:
            data = response.json()
        except Exception:
            frappe.log_error(
                f"""
                API returned invalid JSON

                Employee:
                {employee}

                Device ID:
                {device_id}

                Page:
                {page}

                URL:
                {response.url}

                Response:
                {response.text[:3000]}
                """,
                "Petroka ZKTeco Invalid JSON Response"
            )
            break

        records = data.get("data", [])

        if not records:
            print(f"✅ No records found for {employee} | Device ID: {device_id}")
            break

        print(
            f"📦 Employee={employee} | Device ID={device_id} | "
            f"Page={page} | Records={len(records)}"
        )

        for record in records:
            result = process_record(
                record=record,
                forced_employee=employee,
                expected_emp_code=device_id
            )

            if result == "inserted":
                inserted_count += 1
            else:
                skipped_count += 1

        frappe.db.commit()

        if not data.get("next"):
            break

        page += 1
        sleep(1)

    frappe.log_error(
        f"""
        Employee Sync Finished

        Employee:
        {employee}

        Employee Name:
        {employee_name}

        Device ID:
        {device_id}

        Start Time:
        {start_time}

        End Time:
        {end_time}

        Inserted:
        {inserted_count}

        Skipped:
        {skipped_count}
        """,
        "Petroka ZKTeco Employee Sync Finished"
    )

    return {
        "inserted": inserted_count,
        "skipped": skipped_count
    }


def process_record(record, forced_employee=None, expected_emp_code=None):
    """
    Insert single BioTime punch transaction into ZKtecho Check-In Logs.

    If forced_employee is passed, use that employee directly.
    Otherwise map using:
    ZKTeco emp_code = Employee.attendance_device_id
    """

    emp_code = str(record.get("emp_code") or "").strip()
    first_name = record.get("first_name")
    department = record.get("department")

    punch_time = record.get("punch_time")
    punch_state = str(record.get("punch_state") or "").strip()
    punch_state_display = record.get("punch_state_display")

    terminal_sn = record.get("terminal_sn")
    terminal_alias = record.get("terminal_alias")
    area_alias = record.get("area_alias")
    verify_type_display = record.get("verify_type_display")
    upload_time = record.get("upload_time")

    if not emp_code or not punch_time:
        frappe.log_error(
            f"Skipped invalid record: {record}",
            "Petroka ZKTeco Invalid Record"
        )
        print(f"⚠️ Skipped invalid record: {record}")
        return "skipped"

    if expected_emp_code and emp_code != str(expected_emp_code).strip():
        frappe.log_error(
            f"""
            Skipped record because emp_code mismatch.

            Expected Device ID:
            {expected_emp_code}

            Record emp_code:
            {emp_code}

            Record:
            {record}
            """,
            "Petroka ZKTeco Emp Code Mismatch"
        )
        return "skipped"

    if forced_employee:
        employee = forced_employee
    else:
        employee = frappe.db.get_value(
            "Employee",
            {
                "attendance_device_id": emp_code
            },
            "name"
        )

    if not employee:
        frappe.log_error(
            f"""
            No Employee found for attendance_device_id.

            ZKTeco emp_code:
            {emp_code}

            Name from API:
            {first_name}

            Department from API:
            {department}

            Punch Time:
            {punch_time}
            """,
            "Petroka ZKTeco Employee Mapping Error"
        )

        print(f"⚠️ Employee not found for attendance_device_id: {emp_code}")
        return "skipped"

    log_type = get_log_type(
        punch_state=punch_state,
        punch_state_display=punch_state_display
    )

    exists = frappe.db.exists(
        "ZKtecho Check-In Logs",
        {
            "employee": employee,
            "time": punch_time
        }
    )

    if exists:
        print(f"⏭️ Duplicate skipped: {employee} | {emp_code} | {punch_time}")
        return "skipped"

    doc_data = {
        "doctype": "ZKtecho Check-In Logs",
        "employee": employee,
        "time": punch_time,
        "log_type": log_type,
    }

    meta = frappe.get_meta("ZKtecho Check-In Logs")

    optional_fields = {
        "emp_code": emp_code,
        "attendance_device_id": emp_code,
        "first_name": first_name,
        "department": department,
        "punch_state": punch_state,
        "punch_state_display": punch_state_display,
        "terminal_sn": terminal_sn,
        "terminal_alias": terminal_alias,
        "area_alias": area_alias,
        "verify_type_display": verify_type_display,
        "upload_time": upload_time,
    }

    for fieldname, value in optional_fields.items():
        if meta.has_field(fieldname):
            doc_data[fieldname] = value

    doc = frappe.get_doc(doc_data)

    doc.insert(
        ignore_permissions=True,
        ignore_links=True
    )

    print(
        f"✅ Inserted: Employee={employee} | Device ID={emp_code} | "
        f"{first_name} | {department} | {punch_time} | {log_type}"
    )

    return "inserted"


def get_log_type(punch_state, punch_state_display=None):
    """
    IN / OUT logic.

    Best source:
    punch_state_display:
    Check In  => IN
    Check Out => OUT

    Fallback:
    punch_state 0 => IN
    punch_state 1 => OUT
    """

    punch_state = str(punch_state or "").strip()

    if punch_state_display:
        display = str(punch_state_display).strip().lower()

        if "check in" in display:
            return "IN"

        if "check out" in display:
            return "OUT"

    if punch_state == "0":
        return "IN"

    if punch_state == "1":
        return "OUT"

    if punch_state == "255":
        return "IN"

    frappe.log_error(
        f"Unknown punch_state: {punch_state}, display: {punch_state_display}",
        "Petroka ZKTeco Unknown Punch State"
    )

    return "IN"