import frappe


def after_install():
    set_salary_component()
    set_payroll_settings()


def set_salary_component():
    # first remove old component
    old_components = ["Arrear", "Income Tax"]

    for component in old_components:
        is_exist = frappe.db.exists("Salary Component", {"name": component})
        if is_exist:
            doc = frappe.get_doc("Salary Component", {"name": component})
            doc.flags.ignore_validate = True
            doc.flags.ignore_permissions = True
            doc.flags.ignore_links = True
            doc.delete(force=True)

    # create account

    create_account_if_not_exist(
        account_name="SSF Payabele",
        parent_account="Duties and Taxes - ASP",
        account_type="Payable",
        root_type="Liability",
        report_type="Balance Sheet",
        is_group=False,
    )

    create_account_if_not_exist(
        account_name="Salary TDS Payabele",
        parent_account="Duties and Taxes - ASP",
        account_type="Payable",
        root_type="Liability",
        report_type="Balance Sheet",
        is_group=False,
    )

    create_account_if_not_exist(
        account_name="Salary SST Payabele",
        parent_account="Duties and Taxes - ASP",
        account_type="Payable",
        root_type="Liability",
        report_type="Balance Sheet",
        is_group=False,
    )
    
    create_account_if_not_exist(
        account_name="SSF Expenses",
        parent_account="Indirect Expenses - ASP",
        account_type="Indirect Expense",
        root_type="Expense",
        report_type="Profit & Loss",
        is_group=False,
    )

    # now create new salary component
    new_components = [
        {"name": "Allowance", "abbr": "A", "type": "Earning",
            "account": "Payroll Payable - ASP"},
        {"name": "Dearness Allowance", "abbr": "DA",
            "type": "Earning", "account": "Payroll Payable - ASP"},
        {"name": "Grade", "abbr": "G", "type": "Earning",
            "account": "Payroll Payable - ASP"},
        {"name": "House Rent Allowance", "abbr": "HRA",
            "type": "Earning", "account": "Payroll Payable - ASP"},
        {"name": "Leave Encashment", "abbr": "LE",
            "type": "Earning", "account": "Payroll Payable - ASP"},
        {"name": "Unpaid Leave Deduction", "abbr": "ULD",
            "type": "Deduction", "account": "Payroll Payable - ASP"},
        {"name": "Social Security Fund", "abbr": "SSF",
            "type": "Deduction", "account": "SSF Payabele - ASP"},
        {"name": "Salary TDS", "abbr": "STDS", "type": "Deduction",
            "account": "Salary TDS Payabele - ASP"},
        {"name": "Social Security Tax", "abbr": "SST", "type": "Deduction",
            "account": "Salary TDS Payabele - ASP"},
        {"name": "Company SSF Contribution", "abbr": "CSF", "type": "Earning", "account": "SSF Expenses - ASP", }
    ]
    global_default = frappe.get_doc("Global Defaults")
    for component in new_components:
        is_exist = frappe.db.exists(
            "Salary Component", {"name": component["name"]})
        if not is_exist:
            doc = frappe.get_doc({
                "doctype": "Salary Component",
                "salary_component": component["name"],
                "salary_component_abbr": component["abbr"],
                "type": component["type"],
                "accounts": [
                    {"company": global_default.default_company,
                        "account": component["account"]}
                ],
                "statistical_component": 1 if component["abbr"] == "CSF" else 0
            })
            doc.insert(ignore_permissions=True)


# set initial chart of account
def create_account_if_not_exist(
    account_name,
    parent_account,
    root_type,
    report_type,
    account_type=None,
    is_group=False,
):
    if not frappe.db.exists("Account", {"account_name": account_name}):
        doc = frappe.new_doc("Account")
        doc.account_name = account_name
        doc.parent_account = parent_account
        doc.root_type = root_type
        doc.report_type = report_type
        if account_type:
            doc.account_type = account_type
        doc.is_group = is_group
        doc.save()


def set_payroll_settings():
    doc = frappe.get_doc("Payroll Settings")
    doc.include_holidays_in_total_working_days = 1
    doc.save()
