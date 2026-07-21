# Copyright (c) 2026, Administrator and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class CompanyEvent(Document):
	def autoname(self):
		if not self.event_name:
			frappe.throw("Event Name is required")

		current_date = now_datetime()

		self.name = (
            f"{self.event_name}-"
            f"{current_date.strftime('%m-%Y')}"
        )

