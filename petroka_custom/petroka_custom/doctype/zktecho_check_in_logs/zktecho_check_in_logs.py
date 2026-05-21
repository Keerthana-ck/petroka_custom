import frappe
import requests

from time import sleep
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue


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
        timeout=3600
    )

    frappe.msgprint("✅ Background job has been enqueued.")


def fetch_and_process_data():
    """
    Fetch transactions from Petroka BioTime API and insert into
    ZKtecho Check-In Logs DocType with Employee mapping.
    """

    base_url = "http://petroka.fortiddns.com:8081/iclock/api/transactions/"
    page = 1

    # Optional filters
    start_time = "2026-01-01 00:00:00"
    # end_time = "2026-05-14 23:59:59"
    # emp_code = "100"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",

        # IMPORTANT:
        # Yahan apna fresh Bearer token lagao.
        # Uploaded token ko rotate/change karna better hai.
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5NDI0MDUyLCJpYXQiOjE3NzkzMzc2NTIsImp0aSI6ImEzYjc1YzAzYzE2OTRlZmJiZmVlOGIyN2JlNzZmYzAxIiwidXNlcl9pZCI6MX0.yCrM_OU05ea8YkgY3W48CHQXSnDT6oT619XquMUad0U"
    }

    try:
        while True:
            params = {
                "page": page,

                # Optional filters enable karne ho to uncomment karo
                "start_time": start_time,
                # "end_time": end_time,
                # "emp_code": emp_code,
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
                    Failed to fetch page {page}

                    Status Code:
                    {response.status_code}

                    URL:
                    {response.url}

                    Response:
                    {response.text[:3000]}
                    """,
                    "Petroka ZKTeco API Error"
                )

                print(f"❌ Failed page {page}: {response.status_code}")
                print(response.text)
                break

            try:
                data = response.json()
            except Exception:
                frappe.log_error(
                    f"""
                    API returned 200 but response is not valid JSON.

                    Page:
                    {page}

                    URL:
                    {response.url}

                    Content-Type:
                    {response.headers.get("Content-Type")}

                    Response:
                    {response.text[:3000]}
                    """,
                    "Petroka ZKTeco Invalid JSON Response"
                )

                print("❌ Invalid JSON response. Check Error Log.")
                break

            records = data.get("data", [])

            if not records:
                print("✅ No records found. Finished.")
                break

            print(f"📦 Page {page} - {len(records)} records found")

            for record in records:
                process_record(record)

            frappe.db.commit()

            if not data.get("next"):
                print("✅ No next page. Finished.")
                break

            page += 1
            sleep(1)

    except Exception:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(),
            "Petroka ZKTeco API Fatal Error"
        )
        print("❌ Fatal error. Check Error Log in ERPNext.")


def process_record(record):
    """
    Insert single BioTime punch transaction into ZKtecho Check-In Logs.

    Employee mapping:
        ZKTeco emp_code = Employee.attendance_device_id
        Insert employee = Employee.name
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
        return

    # Employee mapping by attendance_device_id
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
        return

    log_type = get_log_type(
        punch_state=punch_state,
        punch_state_display=punch_state_display
    )

    # Duplicate check should use mapped Employee name, not emp_code
    exists = frappe.db.exists(
        "ZKtecho Check-In Logs",
        {
            "employee": employee,
            "time": punch_time
        }
    )

    if exists:
        print(f"⏭️ Duplicate skipped: {employee} | {emp_code} | {punch_time}")
        return

    doc_data = {
        "doctype": "ZKtecho Check-In Logs",

        # Employee Link field should get actual Employee.name
        "employee": employee,

        "time": punch_time,
        "log_type": log_type,
    }

    meta = frappe.get_meta("ZKtecho Check-In Logs")

    # Add optional fields only if they exist in your custom DocType
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

    # 255 ka meaning device configuration par depend karta hai.
    # Agar aapke server me 255 Check In hota hai to IN rakha hai.
    if punch_state == "255":
        return "IN"

    # Unknown state ko default IN mat karna better hai,
    # lekin existing flow break na ho isliye log karke IN return kar rahe hain.
    frappe.log_error(
        f"Unknown punch_state: {punch_state}, display: {punch_state_display}",
        "Petroka ZKTeco Unknown Punch State"
    )

    return "IN"