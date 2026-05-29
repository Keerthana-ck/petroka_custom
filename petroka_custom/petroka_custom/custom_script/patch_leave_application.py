from hrms.hr.doctype.leave_application.leave_application import LeaveApplication


def apply_patch():
    print("🔥 APPLY PATCH EXECUTED")

    def custom_validate_balance_leaves(self):
        print("🔥 VALIDATION BYPASSED")
        return

    def custom_show_insufficient_balance_message(self, *args, **kwargs):
        print("🔥 POPUP BLOCKED")
        return

    LeaveApplication.validate_balance_leaves = custom_validate_balance_leaves
    LeaveApplication.show_insufficient_balance_message = (
        custom_show_insufficient_balance_message
    )