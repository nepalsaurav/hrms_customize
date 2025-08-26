import math
import frappe
from frappe.auth import date_diff
from frappe.model.document import flt
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
from hrms.hr.doctype.leave_application.leave_application import (
    get_leave_details
)
from frappe.utils import add_days, money_in_words, rounded, today, month_diff
import nepali_datetime
from nepali_datetime import _days_in_month


class CustomSalarySlip(SalarySlip):

    def validate(self):
        self.validate_dates()
        self.check_existing()
        self._set_working_days()
        self._get_default_leave()
        self._get_employee_attendance_status()
        self._add_leaves_in_salary_slip()
        self.set("earnings", [])
        self.set("deductions", [])
        self.set_salary_component()

        # set net pay
        self._calculate_net_pay()
        self.compute_year_to_date()
        self.compute_month_to_date()
        self.compute_component_wise_year_to_date()

    def on_submit(self):
        self.set_status()
        self.update_status(self.name)

    def on_update(self):
        pass

    def on_cancel(self):
        self.set_status()
        self.update_status()

    def _set_working_days(self):
        working_days = date_diff(self.end_date, self.start_date) + 1
        holiday_list = self._get_holidays()
        working_days -= len(holiday_list)
        self.total_working_days = working_days

    def _get_default_leave(self):
        employee_leave_allocation_record = get_leave_details(
            self.employee, today())
        if employee_leave_allocation_record == {}:
            new_leave_allocation_route = f"<a href='/app/leave-control-panel'>Leave Control Panel</a>"
            frappe.throw(frappe._("No leave has been allocated to {0}. Please allocate leave starting from {1}.")
                         .format(
                             frappe.get_desk_link(
                                 "Employee", self.employee, show_title_with_name=True),
                             new_leave_allocation_route
            ))

        self.leave_allocation = employee_leave_allocation_record["leave_allocation"]
        approved_leave = 0
        leaves_pending_for_approve = 0
        frappe.log(employee_leave_allocation_record["leave_allocation"])
        for _, leave_details in employee_leave_allocation_record["leave_allocation"].items():

            approved_leave += leave_details["leaves_taken"]
            leaves_pending_for_approve += leave_details["leaves_pending_approval"]

        self.custom_approved_leave = approved_leave
        self.custom_pending_leave_for_approve = leaves_pending_for_approve

    def _get_holidays(self):
        Holiday = frappe.qb.DocType("Holiday")
        query = (
            frappe.qb.from_(Holiday)
            .select("name", "holiday_date", "description")
            .where(
                Holiday.holiday_date.between(self.start_date, self.end_date)
            )
        )
        holiday_list = query.run(as_dict=True)
        return holiday_list

    def _get_employee_attendance_status(self):
        attendance = frappe.qb.DocType("Attendance")
        attendance_list = (
            frappe.qb.from_(attendance)
            .select(
                attendance.attendance_date,
                attendance.status,
                attendance.leave_type,
                attendance.half_day_status,
            )
            .where(
                (attendance.employee == self.employee)
                & (attendance.docstatus == 1)
                & (attendance.attendance_date.between(self.start_date, self.end_date))
            )
        ).run(as_dict=1)

        # Convert lists to sets for O(1) lookup
        present_days = {
            d.attendance_date for d in attendance_list if d.status == "Present"}
        absent_days_set = {
            d.attendance_date for d in attendance_list if d.status == "Absent"}
        half_days = {
            d.attendance_date for d in attendance_list if d.status == "Half Day"}
        leave_days = {
            d.attendance_date for d in attendance_list if d.status == "On Leave"}
        holidays = {d.holiday_date for d in self._get_holidays()}

        working_days = date_diff(self.end_date, self.start_date) + 1

        self.custom_days_in_month =  working_days
        
        
        absent_days = 0
        unmarked_days = 0

        for i in range(working_days):
            day = add_days(self.start_date, i)

            if day in present_days or day in leave_days or day in holidays:
                continue
            elif day in absent_days_set:
                absent_days += 1
            elif day in half_days:
                absent_days += 0.5
            else:
                absent_days += 1
                unmarked_days += 1

        # Payment days = working days - net absent days (excluding approved leave)
        
        self.working_days = working_days
        self.absent_days = absent_days
        self.payment_days = self.total_working_days - \
            (absent_days - self.custom_approved_leave)
        self.unmarked_days = unmarked_days
        self.leave_without_pay = absent_days - self.custom_approved_leave

    def _add_leaves_in_salary_slip(self):
        leave_details = get_leave_details(self.employee, self.end_date, True)
        for leave_type, leave_values in leave_details["leave_allocation"].items():
            self.append(
                "leave_details",
                {
                    "leave_type": leave_type,
                    "total_allocated_leaves": flt(leave_values.get("total_leaves")),
                    "expired_leaves": flt(leave_values.get("expired_leaves")),
                    "used_leaves": flt(leave_values.get("leaves_taken")),
                    "pending_leaves": flt(leave_values.get("leaves_pending_approval")),
                    "available_leaves": flt(leave_values.get("remaining_leaves")),
                },
            )

    def set_salary_component(self):

        # get salary structure for employee
        salary_structure = frappe.get_doc(
            "Employee Salary Structure", self.employee)

        # append Basic Salary
        self.append("earnings", {
            "salary_component": "Basic",
            "amount": salary_structure.basic
        })

        # append allowance
        self.append("earnings", {
            "salary_component": "Allowance",
            "amount": salary_structure.allowance
        })

        # append dearness allowance
        if salary_structure.dearness_allowance > 0:
            self.append("earnings", {
                "salary_component": "Dearness Allowance",
                "amount": salary_structure.dearness_allowance
            })

        # append ssf contribution
        if salary_structure.is_ssf:
            self.append("deductions", {
                "salary_component": "Social Security Fund",
                "amount": salary_structure.basic * 0.11
            })
            # self.append("earnings", {
            #     "salary_component": "Company SSF Contribution",
            #     "amount": salary_structure.basic * 0.20
            # })

        # append if is grade
        if salary_structure.grade > 0:
            self.append("earnings", {
                "salary_component": "Grade",
                "amount": salary_structure.grade
            })
        # create leave deduction
        if not salary_structure.is_attendance_discard:
            monthly_salary = self._get_monthly_salary(salary_structure)
            working_days = date_diff(self.end_date, self.start_date) + 1
            unpaid_leave_deduction = (
                monthly_salary / working_days) * self.leave_without_pay
            self.append("deductions", {
                "salary_component": "Unpaid Leave Deduction",
                "amount": unpaid_leave_deduction
            })

        if salary_structure.is_attendance_discard:
            self.payment_days = self.total_working_days
            self.leave_without_pay = 0
            self.absent_days = 0
        ctc = self._get_ctc(salary_structure)
        self._tax_calculation(salary_structure, ctc)

    def _get_ctc(self, salary_structure):
        monthly_salary = self._get_monthly_salary(salary_structure)

        ctc = monthly_salary * 12

        employee_detail = frappe.get_doc("Employee", self.employee)
        joining_date_age = month_diff(today(), employee_detail.date_of_joining)

        # add dashain bonus if employee joining date is greater then 6 month:
        if joining_date_age >= 6:
            ctc += monthly_salary * 1

        # add leave encashment
        leave_encashment = monthly_salary * 0.5
        ctc += leave_encashment

        # add house rent allowance if applicable
        if salary_structure.house_rent_allowance:
            ctc += salary_structure.basic * 12 * 0.02

        # if ssf is applicable then add company ssf contribution to ctc
        if salary_structure.is_ssf:
            ctc += salary_structure.basic * 0.20 * 12

        return ctc

    def _get_monthly_salary(self, salary_structure):
        monthly_salary = (
            salary_structure.basic
            + salary_structure.allowance
            + salary_structure.dearness_allowance
            + salary_structure.grade
        )
        return monthly_salary

    def _tax_calculation(self, salary_structure, ctc):

        tax_excemption = 0

        # tax excemption for ssf:
        if salary_structure.is_ssf:
            tax_excemption += min(
                500000,
                1/3 * ctc,
                salary_structure.basic * 12 * 0.31
            )
        # tax excemption for insurance
        if salary_structure.insurance_amount > 0:
            tax_excemption += min(
                40000,
                salary_structure.insurance_amount
            )

        taxable_income = ctc - tax_excemption
        # tds free income
        tds_free = 600_000 if salary_structure.tax_calculation_basic == "Married" else 500_000

        tax = 0

        # slab 1
        if salary_structure.is_ssf:
            tax += 0
        else:
            tax += min(taxable_income * 0.01, tds_free * 0.01)

        # Case 2: 10% slab
        if taxable_income > tds_free:
            tax += min((taxable_income - tds_free) * 0.1, 20000)

        # Case 3: 20% slab
        if taxable_income > (tds_free + 200000):
            tax += min((taxable_income - tds_free - 200000) * 0.2, 60000)

        # Case 4: 30% slab
        if salary_structure.tax_calculation_basic == "Married":
            if taxable_income > 1100000:
                tax += min((taxable_income - 1100000) * 0.3, 270000)
        else:
            if taxable_income > 1000000:
                tax += min((taxable_income - 1000000) * 0.3, 300000)

        # Case 5: 36% slab
        if taxable_income > 2000000:
            tax += max((taxable_income - 2000000) * 0.36, 0)

        # here need to create custom logic for calculte tax based on remaining month
        current_month_tax = math.ceil(tax / 12)

        if taxable_income > tds_free and tax > 0:
            self.append("deductions", {
                "salary_component": "Salary TDS",
                "amount": current_month_tax
            })
        if taxable_income < tds_free and tax > 0:
            self.append("deductions", {
                "salary_component": "Social Security Tax",
                "amount": current_month_tax
            })

        # set tax breakup
        self.tax = tax
        self.ctc = ctc
        self.total_earnings = self.ctc
        self.standard_tax_exemption_amount = tax_excemption
        self.annual_taxable_amount = taxable_income
        self.current_month_income_tax = current_month_tax
        self.future_income_tax_deductions = current_month_tax
        self.previous_total_paid_taxes = self._calculate_income_tax_decuted_till_date()
        self.income_tax_deducted_till_date = self.previous_total_paid_taxes + \
            self.current_month_income_tax
        self.total_income_tax = tax

    def _calculate_net_pay(self):
        self.gross_pay = self.get_component_totals(
            "earnings", depends_on_payment_days=0)
        self.total_deduction = self.get_component_totals(
            "deductions", depends_on_payment_days=0)
        self.net_pay = self.gross_pay - self.total_deduction
        self.rounded_total = self.net_pay
        self.total_in_words = money_in_words(self.rounded_total, self.currency)

    def _calculate_income_tax_decuted_till_date(self):
        fiscal_year = frappe.get_doc("Fiscal Year", {"custom_current": 1})
        previous_paid_taxes = self.get_salary_slip_details(
            fiscal_year.year_start_date,
            self.start_date,
            "Salary TDS"
        )
        if previous_paid_taxes == 0:
            previous_paid_taxes = self.get_salary_slip_details(
                fiscal_year.year_start_date,
                self.start_date,
                "Social Security Tax"
            )
        return previous_paid_taxes
