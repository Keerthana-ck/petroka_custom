from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Leave Application": [
				{
					"fieldname": "future_earned_leave",
					"label": "Future Earned Leave",
					"fieldtype": "Float",
					"insert_after": "total_leave_days",
					"read_only": 1,
					"module": "petroka_custom",
				},
				{
					"fieldname": "total_eligible_leave",
					"label": "Total Eligible Leave",
					"fieldtype": "Float",
					"insert_after": "future_earned_leave",
					"read_only": 1,
					"module": "petroka_custom",
				},
			]
		},
		ignore_validate=True,
	)
