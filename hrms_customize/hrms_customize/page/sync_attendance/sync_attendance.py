import time
import frappe
from frappe import _
from hrms_customize.hrms_customize.doctype.bulk_payroll.bulk_payroll import NEPALI_MONTH_MAP
from hrms_customize.hrms_customize.page.sync_attendance.sync import get_employee_attendance
import nepali_datetime
from nepali_datetime import _days_in_month

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

    start_bs = nepali_datetime.date(int(year), NEPALI_MONTH_MAP[month], 1)
    end_bs = nepali_datetime.date(int(year), NEPALI_MONTH_MAP[month], _days_in_month(
        int(year), NEPALI_MONTH_MAP[month]))

    start_ad = start_bs.to_datetime_date()
    end_ad = end_bs.to_datetime_date()

    month_index = get_year_month_list(start_ad, end_ad)

    frappe.publish_progress(0, title="Syncing...")

    attendance_list = []
    for i, date in enumerate(month_index):
        year, month = date
        attendance = get_employee_attendance(year, month)
        attendance_list.append(attendance)
        if i == 0:
            frappe.publish_progress(25, title="Syncing...")
        if i == 1:
            frappe.publish_progress(50, title="Syncing...")

    employee_biometric_not_exist = set()
    for attendance in attendance_list:
        for key, value in attendance.items():
            employee_exist = frappe.db.exists(
                "Employee", {"attendance_device_id": key})
            if not employee_exist:
                employee_biometric_not_exist.add(value[0]['employee_name'])
                continue
            employee = frappe.get_doc("Employee", employee_exist)
            for v in value:
                attenance_exist = frappe.db.exists(
                    "Attendance", {"employee": employee.name, "attendance_date": v["date"]})

                if attenance_exist:
                    attendance_record = frappe.get_doc(
                        "Attendance", attenance_exist)
                    try:
                        if v["status"] == "P":
                            attendance_record.status = "Present"
                        if v["status"] == "A":
                            attendance_record.status = "Absent"
                        attendance_record.save()
                        continue
                    except:
                        continue

                else:
                    if v["status"] == "P":
                        attendance_record = frappe.get_doc({
                            "doctype": "Attendance",
                            "attendance_date": v["date"],
                            "employee": employee.name,
                            "status": "Present"
                        })
                        attendance_record.insert()
                        # attendance_record.submit()
                    if v["status"] == "A":
                        attendance_record = frappe.get_doc({
                            "doctype": "Attendance",
                            "attendance_date": v["date"],
                            "employee": employee.name,
                            "status": "Absent"
                        })
                        attendance_record.insert()
                        # attendance_record.submit()

    frappe.publish_progress(100, title="Syncing...")

    message = "Succesfully Sync Attendance <br> <br>"
    if len(employee_biometric_not_exist) > 0:
        message += "Following Employee attendance id is not mapped to Employee Records, please map! <br> <br>"
        message += "<ul>"
        message += "".join([f"<li>{emp}</li>" for emp in employee_biometric_not_exist])
        message += "</ul>"
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
