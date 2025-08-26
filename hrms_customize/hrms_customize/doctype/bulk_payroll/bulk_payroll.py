# Copyright (c) 2025, nepalsaurav and contributors
# For license information, please see license.txt

# import frappe
import time
import math
from frappe.auth import date_diff
from frappe.database.database import getdate
from frappe.model.document import Document
import frappe
from frappe.model.docstatus import DocStatus
import nepali_datetime
from nepali_datetime import _days_in_month
from urllib.parse import quote

NEPALI_MONTH_MAP = {
    "Baisakh": 1,
    "Jestha": 2,
    "Ashadh": 3,
    "Shrawan": 4,
    "Bhadra": 5,
    "Ashwin": 6,
    "Kartik": 7,
    "Mangsir": 8,
    "Poush": 9,
    "Magh": 10,
    "Falgun": 11,
    "Chaitra": 12
}


CHANGE_COLUMN_MAP = {
    "year": "custom_year_bs",
    "month": "custom_month_nepali"
}


class BulkPayroll(Document):

    def db_insert(self, *args, **kwargs):
        pass

    def load_from_db(self):
        doc = frappe.get_doc("Payroll Entry", self.name)
        data = doc.as_dict()

        d = {
            "name": data["name"],
            "year": data["custom_year_bs"],
            "month": data["custom_month_nepali"],
            "posting_date": data["posting_date"],
            "docstatus": data["docstatus"],
            "status": data["status"],
            "is_pay_slip_issue": True,
            "modified": data["modified"]
        }

        super(Document, self).__init__(d)

    def db_update(self):
        pass

    def on_cancel(self):
        salays_slips = frappe.get_all("Salary Slip", {"payroll_entry": self.name})
        for name in salays_slips:
            salary_slip = frappe.get_doc("Salary Slip", name)
            salary_slip.cancel()
        payroll_entry = frappe.get_doc("Payroll Entry", self.name)
        payroll_entry.cancel()
        

    def delete(self):
        if self.docstatus == 1:
            frappe.throw(frappe._(
                "Submitable document can not be deleted, you need to first cancel it"))
        
        salays_slips = frappe.get_all("Salary Slip", {"payroll_entry": self.name})
        for name in salays_slips:
            salary_slip = frappe.get_doc("Salary Slip", name)
            salary_slip.delete()
        payroll_entry = frappe.get_doc("Payroll Entry", self.name)
        payroll_entry.delete()

    @frappe.whitelist()
    def submit_document(self):
        self._set_from_date_and_end_date()
        payroll_entry = frappe.get_doc("Payroll Entry",  {"start_date": self.start_date, "end_date": self.end_date})
        payroll_entry.flags.ignore_mandatory = True
        payroll_entry.submit()
        salary_slip = frappe.get_all(
            "Salary Slip", {"payroll_entry": payroll_entry.name})
        for slip in salary_slip:
            doc = frappe.get_doc("Salary Slip", slip)
            doc.flags.ignore_mandatory = True
            doc.submit()

    @staticmethod
    def get_list(filters=None, fields=None, limit=20, start=0, page_length=20, **kwargs):

        for filter in filters:
            filter[0] = "Payroll Entry"
            for i, key in enumerate(filter):
                if key in CHANGE_COLUMN_MAP:
                    filter[i] = CHANGE_COLUMN_MAP[key]

        fields = ["name", "status",
                  "custom_year_bs", "custom_month_nepali"]

        payroll_entries = frappe.get_all(
            doctype="Payroll Entry",
            filters=filters,
            fields=fields,
            limit_start=int(start),
            limit_page_length=int(limit)

        )

        for entries in payroll_entries:
            for key, col in CHANGE_COLUMN_MAP.items():
                if col in entries:
                    entries[key] = entries[col]
                    del entries[col]

        return payroll_entries

    @staticmethod
    def get_count(filters=None, **kwargs):
        pass

    @staticmethod
    def get_stats(**kwargs):
        pass

    @frappe.whitelist()
    def create_salary_slip(self):
        self._set_from_date_and_end_date()
        self._insert_payroll_entry()
        return self._insert_salary_slip()

    def _insert_payroll_entry(self):
        # nedd to validate holiday list exist or not
        self._validate_holiday_exist()
        # need to validate salary strucute is not assign or not
        self._validate_payroll_structure_exist()
        payroll_entry_exist = frappe.db.exists("Payroll Entry", {"start_date": self.start_date, "end_date": self.end_date})
        if not payroll_entry_exist:
            payroll_entry = frappe.get_doc({
                "doctype": "Payroll Entry",
                "posting_date": self.posting_date,
                "company": get_default_company(),
                "payroll_frequency": "Monthly",
                "status": "Draft",
                "start_date": self.start_date,
                "end_date": self.end_date,
                "custom_year_bs": self.year,
                "custom_month_nepali": self.month

            })

            payroll_entry.insert(ignore_mandatory=True,
                                 ignore_permissions=True)
            self.set("payroll_entry", payroll_entry)
            self.name = self.payroll_entry.name
        else:
            payroll_entry = frappe.db.get(
                "Payroll Entry", {"start_date": self.start_date, "end_date": self.end_date})
            self.set("payroll_entry", payroll_entry)
            self.name = payroll_entry.name
            frappe.log(self.name)

    @frappe.whitelist()
    def _insert_salary_slip(self):
        employee_list = frappe.get_all("Employee")
        self.set("salary_slips", [])
        for employee in employee_list:
            SalarySlip = frappe.qb.DocType("Salary Slip")
            is_exist = (
                frappe.qb.from_(SalarySlip)
                .select(SalarySlip.name)
                .where(
                    (SalarySlip.employee == employee["name"])
                    &(SalarySlip.start_date == self.start_date)
                    &(SalarySlip.end_date == self.end_date)
                )
            ).run(as_dict=True)
            
            if len(is_exist) == 0:
                salary_slip_doc = frappe.get_doc({
                    "doctype": "Salary Slip",
                    "employee": employee["name"],
                    "posting_date": self.posting_date,
                    "status": "Draft",
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "payroll_entry": self.payroll_entry.name,
                    "custom_month_name": self.month,
                })
                salary_slip_doc.flags.ignore_mandatory = ["salary_structure"]
                salary_slip_doc.insert()
                self.salary_slips.append(salary_slip_doc)
            if is_exist:
                salary_slip_doc = frappe.get_doc("Salary Slip", {
                    "employee": employee["name"], "start_date": self.start_date, "end_date": self.end_date})
                self.append("salary_slips", salary_slip_doc)

        return_salary_slips = []
        for slips in self.get("salary_slips"):
            return_salary_slips.append({
                "employee": slips.employee,
                "employee_name": slips.employee_name,
                "gross_pay": slips.gross_pay,
                "total_deduction": slips.total_deduction,
                "net_pay": slips.net_pay,
                "link": frappe.get_desk_link("Salary Slip", slips.name, show_title_with_name=True, open_in_new_tab=True)
            })
        return return_salary_slips

    def _set_from_date_and_end_date(self):
        month = NEPALI_MONTH_MAP[self.month]
        year = int(self.year)
        start_date_bs = nepali_datetime.date(year, month, 1)
        start_date_ad = start_date_bs.to_datetime_date()

        end_date_bs = get_month_end(year, month)
        end_date_ad = end_date_bs.to_datetime_date()
        self.start_date = start_date_ad
        self.end_date = end_date_ad

    def _validate_payroll_structure_exist(self):
        error_logs = []
        employee_list = get_employee_list()
        for employee in employee_list:
            structure_is_exist = frappe.db.exists("Employee Salary Structure", {
                                                  "employee": employee["name"]})

            if not structure_is_exist:
                employee_link = frappe.get_desk_link(
                    "Employee", employee["name"], show_title_with_name=True
                )
                error_logs.append(frappe._("Salary structure not define for {0} in {1}").format(
                    employee_link, frappe.bold("Employee Salary Structure")))
        if len(error_logs) > 0:
            frappe.throw(error_logs, as_list=True)

    def _validate_holiday_exist(self):
        """
        This function validates whether a Holiday List
        has been created for the posting fiscal year.
        If no Holiday List exists for that fiscal year, it will throw an error.
        """
        fiscal_year = self._get_current_fiscal()
        # throw error if fiscal year length is 0
        if len(fiscal_year) == 0:
            frappe.throw("Fiscal year not set")

        holiday_list = self._get_current_holiday(fiscal_year)

        if len(holiday_list) == 0:
            frappe.throw(frappe._("Holiday list has not been created for Fiscal Year {0}").format(
                fiscal_year[0]["name"]))

    def _get_current_holiday(self, fiscal_year):
        # check holiday list for that fiscal year
        HolidayList = frappe.qb.DocType("Holiday List")
        holiday_list = (
            frappe.qb.from_("Holiday List").select("name")
            .where(
                (fiscal_year[0]["year_start_date"] == HolidayList.from_date)
                & (fiscal_year[0]["year_end_date"] == HolidayList.to_date)
            )
        ).run(as_dict=True)
        return holiday_list

    def _get_current_fiscal(self):
        FiscalYear = frappe.qb.DocType("Fiscal Year")
        fiscal_year = (
            frappe.qb.from_("Fiscal Year").select(
                "name", "year_start_date", "year_end_date")
            .where(
                (FiscalYear.year_start_date <= self.posting_date)
                & (FiscalYear.year_end_date >= self.posting_date)
            )
        ).run(as_dict=True)
        return fiscal_year

    @frappe.whitelist()
    def get_current_year(self):
        today = nepali_datetime.date.today()
        month = ""
        for name, num in NEPALI_MONTH_MAP.items():
            if num == today.month:
                month = name
                break
        return {
            "year": today.year,
            "month": month
        }

    @frappe.whitelist()
    def get_holiday_info(self):
        self._set_from_date_and_end_date()
        Holiday = frappe.qb.DocType("Holiday")
        query = (
            frappe.qb.from_(Holiday)
            .select("name", "holiday_date", "description", "parent")
            .where(
                Holiday.holiday_date.between(self.start_date, self.end_date)
            )
        )
        holiday_list = query.run(as_dict=True)
        holiday_list = sorted(
            holiday_list, key=lambda x: x["holiday_date"], reverse=False)
        for holiday in holiday_list:
            bs_date = nepali_datetime.date.from_datetime_date(
                holiday["holiday_date"])
            holiday["bs_date"] = bs_date.strftime("%Y-%m-%d")

        html_content = "<table class='table table-bordered table-sm'>"
        if len(holiday_list) > 0:
            html_content += """
            <thead>
            <th>AD Date</th>
            <th>BS Date</th>
            <th>Description</th>
            </thead>
            """
            html_content += "<tbody>"
            for holiday in holiday_list:
                html_content += f"""
                <tr>
                <td>{holiday["holiday_date"]}</td>
                <td>{holiday["bs_date"]}</td>
                <td>{holiday["description"]}</td>
                </tr>
                """
            html_content += "</tbody>"
        html_content += "</table>"

        holiday = self.get_current_holiday()

        if holiday:
            html_content += f"""
            If holiday is missing, then add holiday from: {safe_desk_link("Holiday List", holiday, show_title_with_name=True)}
            """
        else:
            html_content += f"""
            If holiday is missing then create holiday from: {frappe.new_doc("Holiday List")}
            """

        return html_content

    def get_current_holiday(self):
        fiscal_year = self._get_current_fiscal()
        is_exist = frappe.db.exists("Holiday List", {
                                    "from_date": fiscal_year[0].year_start_date, "to_date": fiscal_year[0].year_end_date})
        return is_exist


def get_default_company():
    global_defaults = frappe.get_doc("Global Defaults")
    return global_defaults.default_company


def get_month_end(year, month):
    days_in_month = _days_in_month(year, month)
    month_end_date = nepali_datetime.date(year, month, days_in_month)
    return month_end_date


def get_employee_list():
    employee_list = frappe.get_list(
        doctype="Employee",
        fields=["name", "employee_name"]
    )
    return employee_list


def safe_desk_link(doctype, name, show_title_with_name=False):
    safe_name = quote(name, safe="")  # encode /, spaces, etc.
    return frappe.get_desk_link(doctype, safe_name, show_title_with_name=show_title_with_name)
