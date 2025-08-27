import time
import frappe
from frappe import _
from hrms_customize.hrms_customize.doctype.bulk_payroll.bulk_payroll import NEPALI_MONTH_MAP
from hrms_customize.hrms_customize.page.sync_attendance.sync import get_employee_attendance
import nepali_datetime
from nepali_datetime import _days_in_month
import frappe
import nepali_datetime
from frappe.utils import getdate
from frappe import _

STATUS_MAP = {
    "P": "Present",
    "A": "Absent"
}


@frappe.whitelist()  # ← This makes it callable from client-side


def sync_attendance(year, month):
    if not year:
        frappe.throw(_("Year is required"))
    if not month:
        frappe.throw(_("Month is required"))

    # Convert Nepali month to AD
    start_bs = nepali_datetime.date(int(year), NEPALI_MONTH_MAP[month], 1)
    end_bs = nepali_datetime.date(int(year), NEPALI_MONTH_MAP[month], _days_in_month(int(year), NEPALI_MONTH_MAP[month]))

    start_ad = start_bs.to_datetime_date()  # date object
    end_ad = end_bs.to_datetime_date()      # date object

    month_index = get_year_month_list(start_ad, end_ad)

    total_days = len(month_index)
    frappe.publish_progress(0, title="Syncing attendance...")

    employee_biometric_not_exist = set()

    for i, (y, m) in enumerate(month_index):
        attendance = get_employee_attendance(y, m)

        for device_id, records in attendance.items():
            employee_exist = frappe.db.exists("Employee", {"attendance_device_id": device_id})
            if not employee_exist:
                employee_biometric_not_exist.add(records[0]['employee_name'])
                continue

            employee = frappe.get_doc("Employee", employee_exist)

            for record in records:
                check_date = getdate(record["date"])  # safe conversion to date

                if not start_ad <= check_date <= end_ad:
                    continue

                attendance_exist = frappe.db.exists(
                    "Attendance", {"employee": employee.name, "attendance_date": check_date}
                )

                status = "Present" if record["status"] == "P" else "Absent"

                if attendance_exist:
                    # Update existing record
                    attendance_doc = frappe.get_doc("Attendance", attendance_exist)
                    try:
                        if attendance_doc.status != "Present" or attendance_doc.status == "On Leave":
                            attendance_doc.status = status
                            attendance_doc.save()
                    except:
                        continue
                else:
                    # Create new record
                    frappe.get_doc({
                        "doctype": "Attendance",
                        "employee": employee.name,
                        "attendance_date": check_date,
                        "status": status
                    }).insert()

        # Update progress
        progress_percent = int((i + 1) / total_days * 100)
        frappe.publish_progress(progress_percent, title="Syncing attendance...")

    # Build message
    message = "Successfully synced attendance.<br><br>"
    if employee_biometric_not_exist:
        message += "Following Employee attendance IDs are not mapped to Employee Records, please map!<br><br>"
        message += "<ul>" + "".join([f"<li>{emp}</li>" for emp in employee_biometric_not_exist]) + "</ul>"

    return frappe.msgprint(message)



def get_year_month_list(start_ad, end_ad):
    result = []
    current = start_ad.replace(day=1)

    while current <= end_ad:
        # Convert both year and month to string
        result.append([str(current.year), f"{current.month:02d}"])

        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return result
