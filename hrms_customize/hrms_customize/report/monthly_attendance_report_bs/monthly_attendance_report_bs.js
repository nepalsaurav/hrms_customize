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
		console.log(report);
		report.set_filter_value("year", r.message.year);
		report.set_filter_value("month", r.message.month);
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
		return value
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
