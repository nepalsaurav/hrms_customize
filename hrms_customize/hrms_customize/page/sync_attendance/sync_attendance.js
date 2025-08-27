frappe.pages["sync-attendance"].on_page_load = async function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Sync Attendance",
		single_column: true,
	});

	let year = page.add_field({
		label: "Year",
		fieldtype: "Select",
		fieldname: "year",
		options:
			"\n2080\n2081\n2082\n2083\n2084\n2085\n2086\n2087\n2088\n2089\n2090\n2091\n2092\n2093\n2094\n2095\n2096\n2097\n2098\n2099",
		mandatory: 1,
	});

	let month = page.add_field({
		fieldname: "month",
		fieldtype: "Select",
		label: "Month",
		mandatory: 1,
		options:
			"\nBaisakh\nJestha\nAshadh\nShrawan\nBhadra\nAshwin\nKartik\nMangsir\nPoush\nMagh\nFalgun\nChaitra",
	});

	// set default month value
	const r = await frappe.call({
		method: "hrms_customize.hrms_customize.report.monthly_attendance_report_bs.monthly_attendance_report_bs.get_year_month",
	});
	year.set_value(r.message.year);
	month.set_value(r.message.month);

	page.add_inner_button("Sync Attendance", function (btn) {
		let values = page.get_form_values();
		let $btn = $(btn); // get jQuery object of the button

		// Disable the button immediately
		$btn.prop("disabled", true).text("Syncing...");
		frappe.call({
			method: "hrms_customize.hrms_customize.page.sync_attendance.sync_attendance.sync_attendance",
			args: values,
			callback: function (r) {
				$btn.prop("disabled", false).text("Sync Attendance");
			},
		});
	}).addClass("btn-primary");
};
