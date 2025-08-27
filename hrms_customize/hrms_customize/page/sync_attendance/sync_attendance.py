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



@frappe.whitelist()
def sync_attendance(year, month):
    if not year:
        frappe.throw(_("Year is required"))
    if not month:
        frappe.throw(_("Month is required"))

    # Convert Nepali month to AD
    start_bs = nepali_datetime.date(int(year), NEPALI_MONTH_MAP[month], 1)
    end_bs = nepali_datetime.date(
        int(year), NEPALI_MONTH_MAP[month], _days_in_month(int(year), NEPALI_MONTH_MAP[month])
    )

    start_ad = start_bs.to_datetime_date()
    end_ad = end_bs.to_datetime_date()

    month_index = get_year_month_list(start_ad, end_ad)

    # Get all holidays in the period
    Holiday = frappe.qb.DocType("Holiday")
    holiday_list = (
        frappe.qb.from_(Holiday)
        .select(Holiday.holiday_date)
        .where(Holiday.holiday_date.between(start_ad, end_ad))
        .run(as_dict=True)
    )
    holidays = {getdate(h.holiday_date) for h in holiday_list}

    employee_biometric_not_exist = set()
    all_records = []

    # Collect all attendance records first to calculate progress
    for y, m in month_index:
        attendance = get_employee_attendance(y, m)
        for device_id, records in attendance.items():
            for record in records:
                all_records.append((device_id, record))

    total_records = len(all_records)
    if total_records == 0:
        return frappe.msgprint("No attendance records to sync.")

    for idx, (device_id, record) in enumerate(all_records, start=1):
        try:
            employee_exist = frappe.db.exists("Employee", {"attendance_device_id": device_id})
            if not employee_exist:
                employee_biometric_not_exist.add(record['employee_name'])
                continue

            employee = frappe.get_doc("Employee", employee_exist)
            check_date = getdate(record["date"])

            # Skip if the date is a holiday or weekly off (Saturday)
            if check_date in holidays or check_date.weekday() == 5:
                continue

            if not start_ad <= check_date <= end_ad:
                continue

            status = "Present" if record["status"] == "P" else "Absent"

            attendance_exist = frappe.db.exists(
                "Attendance", {"employee": employee.name, "attendance_date": check_date}
            )

            if attendance_exist:
                attendance_doc = frappe.get_doc("Attendance", attendance_exist)
                attendance_doc.status = status
                attendance_doc.save()
            else:
                frappe.get_doc({
                    "doctype": "Attendance",
                    "employee": employee.name,
                    "attendance_date": check_date,
                    "status": status
                }).insert()

        except Exception as e:
            frappe.log_error(
                message=str(e),
                title=f"Attendance Sync Error for {device_id} on {record['date']}"
            )

        # Update progress
        progress_percent = int(idx / total_records * 100)
        frappe.publish_progress(progress_percent, title="Syncing attendance...")

    # Build message
    message = "✅ Successfully synced attendance.<br><br>"
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
