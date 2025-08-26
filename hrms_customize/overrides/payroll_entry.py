import frappe
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry


class CustomPayrollEntry(PayrollEntry):
    def validate(self):
        self._validate_dublicate_payroll_entry()
    
    def before_submit(self):
        self.validate_existing_salary_slips()
        if self.get_employees_with_unmarked_attendance():
            frappe.throw(
                frappe._("Cannot submit. Attendance is not marked for some employees."))

    def on_submit(self):
        self.set_status(update=True, status="Submitted")

    def on_cancel(self):
        # need to cancel salary slips
        self.set_status(update=True, status="Cancelled")
    
    def _validate_dublicate_payroll_entry(self):
        is_exist = frappe.db.exists(
            "Payroll Entry", {"start_date": self.start_date, "end_date": self.end_date, "docstatus": 1}
        )
        if is_exist:
            frappe.throw(frappe._("Payroll Entry already exists for {0} and {1}").format(frappe.bold(self.start_date), frappe.bold(self.end_date)))
   
        