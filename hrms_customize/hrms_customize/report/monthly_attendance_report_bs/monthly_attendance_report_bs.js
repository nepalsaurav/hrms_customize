// Copyright (c) 2025, nepalsaurav and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Attendance Report BS"] = {
	filters: [
		{
			fieldname: "year",
			fieldtype: "Select",
			label: "Year",
			mandatory: 1,
			options:
				"\n2080\n2081\n2082\n2083\n2084\n2085\n2086\n2087\n2088\n2089\n2090\n2091\n2092\n2093\n2094\n2095\n2096\n2097\n2098\n2099",
			wildcard_filter: 0,
		},
		{
			fieldname: "month",
			fieldtype: "Select",
			label: "Month",
			mandatory: 1,
			options:
				"\nBaisakh\nJestha\nAshadh\nShrawan\nBhadra\nAshwin\nKartik\nMangsir\nPoush\nMagh\nFalgun\nChaitra",
			wildcard_filter: 0,
		},
	],

	async onload(report) {
		const r = await frappe.call({
			method: "hrms_customize.hrms_customize.report.monthly_attendance_report_bs.monthly_attendance_report_bs.get_year_month",
		});
	
		report.set_filter_value("year", r.message.year);
		report.set_filter_value("month", r.message.month);


		report.page.add_inner_button("Submit Attendance", async () => {
			frappe.confirm("Are you sure you want to submit attendance, after this you can not edit", () => {
				const year = frappe.query_report.get_filter_value("year")
				const month = frappe.query_report.get_filter_value("month")
				frappe.call({
					method: "hrms_customize.hrms_customize.report.monthly_attendance_report_bs.monthly_attendance_report_bs.submit_attendance",
					args: {year, month},
					callback: (r) => {
						console.log(r)
					}
				})
			})
		}).addClass("btn-primary")
	},

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.colIndex > 3 || column.colIndex > 2) {
			if (value == "HD/P") value = "<span style='color:#914EE3'>" + value + "</span>";
			else if (value == "HD/A") value = "<span style='color:orange'>" + value + "</span>";
			else if (value == "P" || value == "WFH")
				value = "<span style='color:green'>" + value + "</span>";
			else if (value == "A") value = "<span style='color:red'>" + value + "</span>";
			else if (value == "L") value = "<span style='color:#318AD8'>" + value + "</span>";
			else value = "<span style='color:#878787'>" + value + "</span>";
		}
		return value;
	},
};

async function getDefault() {
	const r = await frappe.call({
		method: "hrms_customize.hrms_customize.report.monthly_attendance_report_bs.monthly_attendance_report_bs.get_year_month",
	});
	// console.log(r);
	// return r.message.year
	return "2083";
}

$("<style>")
	.prop("type", "text/css")
	.html(
		`
        .dt-cell {
            cursor: pointer;
        }
    `
	)
	.appendTo("head");

const NEPALI_MONTH_MAP = {
	Baisakh: "01",
	Jestha: "02",
	Ashadh: "03",
	Shrawan: "04",
	Bhadra: "05",
	Ashwin: "06",
	Kartik: "07",
	Mangsir: "08",
	Poush: "09",
	Magh: "10",
	Falgun: "11",
	Chaitra: "12",
};

$(document).on("click", ".dt-cell", async function (event) {
	let parentRow = $(event.target).closest(".dt-row");
	let employee = parentRow.children().eq(1).text().trim();
	let employee_name = parentRow.children().eq(2).text().trim();
	let clickedCell = $(event.target).closest(".dt-cell");
	let cellIndex = clickedCell.index();
	let headerRow = $(".dt-row-header");
	let date = headerRow.children().eq(cellIndex).text().trim();
	if (cellIndex >= 3) {
		console.log(employee, employee_name, date, cellIndex);
		let bs_date = date.split(" ")[0].padStart(2, "0");
		let month = NEPALI_MONTH_MAP[frappe.query_report.get_filter_value("month")];
		bs_date = `${frappe.query_report.get_filter_value("year")}-${month}-${bs_date}`;
		const resp = await frappe.call({
			method: "hrms_customize.hrms_customize.report.monthly_attendance_report_bs.monthly_attendance_report_bs.convert_nepali_to_ad",
			args: { date: bs_date },
		});
		const ad_date = resp.message;

		let dialog = new frappe.ui.Dialog({
			title: "Mark Attendance",
			fields: [
				{
					label: "Employee",
					fieldname: "employee",
					fieldtype: "Link",
					default: employee,
					read_only: 1,
				},
				{
					label: "Employee Name",
					fieldname: "employee_name",
					fieldtype: "Data",
					default: employee_name,
					read_only: 1,
				},
				{
					label: "Attendance Date",
					fieldname: "attendance_date",
					fieldtype: "Date",
					default: ad_date,
					read_only: 1,
				},
				{
					label: "Attendance Date BS",
					fieldname: "attendance_date_bs",
					fieldtype: "Data",
					default: bs_date,
					read_only: 1,
				},
				{
					label: "Status",
					fieldname: "status",
					fieldtype: "Select",
					options: "Present\nAbsent",
					default: "Present",
				},
			],
			size: "small",
			primary_action_label: "Save",
			async primary_action(values) {
				const attendance_record = await frappe.db.get_doc("Attendance", null, {
					"employee": values.employee,
					"attendance_date": values.attendance_date
				})
				await frappe.db.set_value("Attendance", attendance_record.name, "status", values.status)
				dialog.hide();
				frappe.query_report.refresh();
			},
		});

		dialog.show();

		console.log(ad_date);
	}
});
