// Copyright (c) 2026, Administrator and contributors
// For license information, please see license.txt

frappe.ui.form.on("Work Request Form", {
    onload(frm) {
        if (frm.is_new() && !frm.doc.employee) {
            frm.set_value("company", "");
            frm.set_value("email", "");
        }
    },

    company(frm) {
        if (frm.doc.company) {
            set_company_email(frm);
        } else {
            frm.set_value("email", "");
        }
    }
});


async function set_company_email(frm) {
    if (!frm.doc.company) {
        return;
    }

    // First try the email stored directly in Company.
    const company_response = await frappe.db.get_value(
        "Company",
        frm.doc.company,
        "email"
    );

    const company_email = company_response.message?.email;

    if (company_email) {
        await frm.set_value("email", company_email);
        return;
    }

    // Otherwise fetch the email from the linked Company Address.
    const address_response = await frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Address",
            filters: [
                ["Dynamic Link", "link_doctype", "=", "Company"],
                ["Dynamic Link", "link_name", "=", frm.doc.company]
            ],
            fields: [
                "`tabAddress`.name",
                "`tabAddress`.email_id",
                "`tabAddress`.is_primary_address"
            ],
            order_by:
                "`tabAddress`.is_primary_address desc, `tabAddress`.modified desc",
            limit_page_length: 1
        }
    });

    const address = address_response.message?.[0];

    if (address?.email_id) {
        await frm.set_value("email", address.email_id);
    } else {
        await frm.set_value("email", "");

        frappe.show_alert({
            message: __(
                "No email was found in the Company or its linked Address."
            ),
            indicator: "orange"
        });
    }
}