// Copyright (c) 2025, nepalsaurav and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bulk Payroll", {
	async refresh(frm) {
		if (!frm.is_new()) {
			frm.set_df_property("year", "read_only", 1);
			frm.set_df_property("month", "read_only", 1);
			frm.set_df_property("posting_date", "read_only", 1);
		}
		if (frm.doc.docstatus === 0) {
			frm.fields_dict.salary_slips_list.html("");
		}

		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Cancel"), () => {
				frappe.confirm("Are you sure want to cancel", () => {
					frm.save("Cancel");
					frm.refresh();
				});
			});
		}

		frm.trigger("get_holiday_list");

		// hide save button
		frm.page.btn_primary.hide();
		// add context button

		// get current year as default year
		if (!frm.doc.year || !frm.doc.month) {
			frappe.call({
				doc: frm.doc,
				method: "get_current_year",
				callback: (r) => {
					frm.set_value("year", r.message.year);
					frm.set_value("month", r.message.month);
				},
			});
		}

		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Create Salary Slips"), () => {
				get_salary_slips(frm);
			}).addClass("btn-primary");
			if (!frm.is_new()) {
				get_salary_slips(frm);
			}
		}

		if (frm.doc.docstatus === 1) {
			get_salary_slips(frm, (submit_button = false));
		}
	},

	custom_button: function (frm) {
		frm.add_custom_button(__("Submit"), () => {
			frappe.confirm("Are you sure you want to save Salary Slips permanently?", () => {
				frm.call({
					doc: frm.doc,
					method: "submit_document",
					callback: () => {
						frm.remove_custom_button("Submit");
						frappe.msgprint(__('Salary Slips submited successfully'));
					},
				});
			});
		}).addClass("btn-primary");
	},

	get_holiday_list: function (frm) {
		frm.add_custom_button(__("Get Holiday Info"), async () => {
			if (frm.doc.year === null || frm.doc.month === null || frm.doc.posting_date === null) {
				frappe.throw(__("Please enter all required field!"));
			}

			frappe.call({
				doc: frm.doc,
				method: "get_holiday_info",
				callback: (r) => {
					frappe.msgprint({
						title: __(`Holiday List for month of ${frm.doc.month}`),
						indicator: "green",
						message: r.message,
					});
				},
			});
		});
	},
});

function get_salary_slips(frm, submit_button = true) {
	frm.remove_custom_button("Create Salary Slips");
	frappe.call({
		doc: frm.doc,
		method: "create_salary_slip",
		callback: (r) => {
			if (r.message.length > 0) {
				const mapped_data = r.message.map((e) => [
					e.employee,
					e.employee_name,
					e.gross_pay,
					e.total_deduction,
					e.net_pay,
					e.link,
				]);
				create_salary_slip_table(frm, mapped_data);

				// now create custom submit button
				if (submit_button) {
					frm.trigger("custom_button");
				}
			}
		},
	});
}

function create_salary_slip_table(frm, data) {
	const data_table_div = document.createElement("div");
	data_table_div.setAttribute("id", "data_table");
	frm.fields_dict.salary_slips_list.html(data_table_div.outerHTML);
	new DataTable("#data_table", {
		columns: [
			"Employee",
			"Employee Name",
			"Gross Pay",
			"Total Deduction",
			"Net Pay",
			"Salary Slip",
		],
		data: data,
	});
}
