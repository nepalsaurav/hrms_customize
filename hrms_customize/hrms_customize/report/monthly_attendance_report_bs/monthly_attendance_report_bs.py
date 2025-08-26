# Copyright (c) 2025, nepalsaurav and contributors
# For license information, please see license.txt

# import frappe
from frappe import _
import frappe
from frappe.auth import date_diff
from frappe.email.receive import add_days
from hrms_customize.hrms_customize.doctype.bulk_payroll.bulk_payroll import NEPALI_MONTH_MAP, get_month_end
import nepali_datetime


status_map = {
	"Present": "P",
	"Absent": "A",
	"Half Day/Other Half Absent": "HD/A",
	"Half Day/Other Half Present": "HD/P",
	"Work From Home": "WFH",
	"On Leave": "L",
	"Holiday": "H",
	"Weekly Off": "WO",
}


day_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def execute(filters: dict | None = None):
    """Return columns and data for the report.

    This is the main entry point for the report. It accepts the filters as a
    dictionary and should return columns and data. It is called by the framework
    every time the report is refreshed or a filter is updated.
    """
    columns = get_columns(filters)
    data = get_data(filters)

    return columns, data


def get_columns(filters) -> list[dict]:
    """Return columns for the report.

    One field definition per column, just like a DocType field definition.
    """
    start_date_ad, end_date_ad = get_from_date_and_end_date(filters)
    working_days = date_diff(end_date_ad, start_date_ad) + 1

    columns = [
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Data",
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
        },
    ]

    reversed_dict = {v: k for k, v in NEPALI_MONTH_MAP.items()}

    for i in range(working_days):
        day = add_days(start_date_ad, i)
        bs_date = nepali_datetime.date.from_datetime_date(day)
        weekday = day_abbr[day.weekday()]
        label = f"{bs_date.day} {weekday}"

        columns.append({
            "label": label,
            "fieldname": _("{0}").format(bs_date.day),
            "fieldtype": "Data"
        })
    return columns


def get_data(filters) -> list[list]:
    """Return data for the report.

    The report data is a list of rows, with each row being a list of cell values.
    """
    start_date_ad, end_date_ad = get_from_date_and_end_date(filters)

    Attendance = frappe.qb.DocType("Attendance")
    Employee = frappe.qb.DocType("Employee")
    Holiday = frappe.qb.DocType("Holiday")
    attendance_query = (
        frappe.qb.from_(Attendance)
        .join(Employee)
        .on(Employee.name == Attendance.employee)
        .select(
            Attendance.employee,
            Employee.employee_name,
            Attendance.attendance_date,
            Attendance.status,
        )
        .where(
            Attendance.attendance_date.between(
                start_date_ad, end_date_ad)
        )
    )
    attendance_list = attendance_query.run(as_dict=True)

    holiday_query = (
        frappe.qb.from_(Holiday)
        .select(
            Holiday.holiday_date,
            Holiday.description
        )
        .where(
            Holiday.holiday_date.between(start_date_ad, end_date_ad)
        )
    )
    holiday_list = holiday_query.run(as_dict=True)

    holiday_list = [h.holiday_date for h in holiday_list]

    return_dict = {}

    for attendance in attendance_list:
        return_dict[attendance.employee] = {
            "employee": attendance.employee,
            "employee_name": attendance.employee_name
        }

    working_days = date_diff(end_date_ad, start_date_ad) + 1
    for i in range(working_days):
        day = add_days(start_date_ad, i)
        for attendance in attendance_list:
            if attendance.attendance_date == day:
                frappe.log(attendance.status)
                return_dict[attendance.employee][day] = status_map[attendance.status]
            elif day in holiday_list:
                if day.weekday() == 5:
                    return_dict[attendance.employee][day] = "WO"
                else:
                    return_dict[attendance.employee][day] = "H"
            else:
                return_dict[attendance.employee][day] = "A"

    items = []
    
    for _, value in return_dict.items():
        d = list(value.values())
        items.append(d)

    frappe.log(items)
    return items


def get_from_date_and_end_date(filters):
    month = NEPALI_MONTH_MAP[filters.month]
    year = int(filters.year)
    start_date_bs = nepali_datetime.date(year, month, 1)
    start_date_ad = start_date_bs.to_datetime_date()

    end_date_bs = get_month_end(year, month)
    end_date_ad = end_date_bs.to_datetime_date()
    return start_date_ad, end_date_ad


@frappe.whitelist()
def get_year_month():
    today_date = nepali_datetime.date.today()
    reversed_dict = {v: k for k, v in NEPALI_MONTH_MAP.items()}
    return {
        "year": today_date.year,
        "month": reversed_dict[today_date.month]
    }
