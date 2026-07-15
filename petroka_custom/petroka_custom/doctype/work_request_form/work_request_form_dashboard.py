from frappe import _

def get_data():
	return {
		"fieldname": "work_request_list",
		"non_standard_fieldnames": {
			"Leave Allocation": "work_request_list"
		},
		"transactions": [
			{
				"label": _("Related"),
				"items": ["Leave Allocation"]
			}
		],
	}