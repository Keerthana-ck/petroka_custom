import frappe
from frappe.desk.form.assign_to import add

def assign_task_to_creator(doc, method):
	# print("ssssssssssssssssssss")
	add({
		"assign_to": [doc.owner],
		"doctype": doc.doctype,
		"name": doc.name,
		"description": f"Task assigned to {doc.owner}"
	})