import frappe
from frappe import _
from frappe.desk.form.assign_to import add, remove

def assign_task_to_creator(doc, method):
	
	add({
		"assign_to": [doc.owner],
		"doctype": doc.doctype,
		"name": doc.name,
		"description": f"Task assigned to {doc.owner}"
	})

def task_assign_to_selected_employee(doc, method=None):
	"""
	Remove the previous employee assignment and
	assign the Task to the newly selected employee.
	"""

	old_doc = doc.get_doc_before_save()

	old_employee = (
		old_doc.custom_employee
		if old_doc
		else None
	)

	new_employee = doc.custom_employee

	if old_employee == new_employee:
		return

	if old_employee:
		old_user = frappe.db.get_value(
			"Employee",
			old_employee,
			"user_id",
		)

		if old_user:
			remove(
				doc.doctype,
				doc.name,
				old_user,
			)

	if not new_employee:
		return

	new_user = frappe.db.get_value(
		"Employee",
		new_employee,
		"user_id",
	)

	if not new_user:
		frappe.throw(
			_("No user is linked with Employee {0}.").format(
				new_employee
			)
		)

	add(
		{
			"assign_to": [new_user],
			"doctype": doc.doctype,
			"name": doc.name,
			"description": _(
				"Task assigned to {0}"
			).format(new_employee),
		}
	)