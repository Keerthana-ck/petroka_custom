app_name = "petroka_custom"
app_title = "petroka_custom"
app_publisher = "Administrator"
app_description = "Custom App for Petroka"
app_email = "admin@gmail.com"
app_license = "mit"

# Leave Application balance validation is customized via override_doctype_class below.
# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
#   {
#       "name": "petroka_custom",
#       "logo": "/assets/petroka_custom/logo.png",
#       "title": "petroka_custom",
#       "route": "/petroka_custom",
#       "has_permission": "petroka_custom.api.permission.has_app_permission"
#   }
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/petroka_custom/css/petroka_custom.css"
# app_include_js = "/assets/petroka_custom/js/petroka_custom.js"

# include js, css files in header of web template
# web_include_css = "/assets/petroka_custom/css/petroka_custom.css"
# web_include_js = "/assets/petroka_custom/js/petroka_custom.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "petroka_custom/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Leave Application" : "public/js/leave_application.js",
    "Expense Claim" : "public/js/expense_claim.js",
    "Work Request Form" : "public/js/work_request_from.js",
    "Task" : "public/js/task.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "petroka_custom/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#   "Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#   "methods": "petroka_custom.utils.jinja_methods",
#   "filters": "petroka_custom.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "petroka_custom.install.before_install"
# after_install = "petroka_custom.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "petroka_custom.uninstall.before_uninstall"
# after_uninstall = "petroka_custom.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "petroka_custom.utils.before_app_install"
# after_app_install = "petroka_custom.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "petroka_custom.utils.before_app_uninstall"
# after_app_uninstall = "petroka_custom.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "petroka_custom.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#   "Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#   "Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# Override standard Leave Application validation for future earned leave booking.
override_doctype_class = {
    "Leave Application": "petroka_custom.overrides.leave_application.CustomLeaveApplication"
}

# Document Events
# ---------------
# Hook on document methods and events
doc_events = {
    "Task": {
        "after_insert": "petroka_custom.overrides.task.assign_task_to_creator",
        "on_update": "petroka_custom.overrides.task.task_assign_to_selected_employee"
    },
    # "Leave Application": {
    #     "validate": "petroka_custom.doc_event.validate_bereavement_leave"
    # },
    "Leave Application": {
        "validate": [
            "petroka_custom.doc_event.validate_bereavement_leave",
            "petroka_custom.petroka_custom.custom_script.leave_application.validate_future_draft_leave"
        ]
    },
    "Employee Certificates and Documents":{
        "validate": "petroka_custom.doc_event.set_hr_manager"
    },
    "Expense Claim": {
        "validate": "petroka_custom.doc_event.validate_air_ticket_allowance",
    }
}

# Scheduled Tasks
# ---------------



scheduler_events = {
#   "all": [
#       "petroka_custom.tasks.all"
#   ],
    "daily": [
        "petroka_custom.doc_event.expire_leave_allocation",
        "petroka_custom.petroka_custom.doctype.work_request_form.work_request_form.expire_leave_allocation"
    ],
    # "daily": [
    #     "petroka_custom.petroka_custom.custom_script.zkteco.enqueue_sync_zkteco_logs"
    # ],
    "hourly": [
        "petroka_custom.petroka_custom.doctype.zktecho_check_in_logs.zktecho_check_in_logs.enqueue_fetch_and_process_data"
    ],
    
    # "cron": {
    #     "0 0 * * *": [
    #         "petroka_custom.petroka_custom.custom_script.zkteco.enqueue_sync_zkteco_logs"
    #     ]
    # }
    "cron": {
        "* * * * *": [
            "petroka_custom.petroka_custom.custom_script.zkteco.sync_morning_checkins"
        ],
        "0 23 * * *": [
            "petroka_custom.petroka_custom.custom_script.zkteco.enqueue_sync_zkteco_logs"
        ]
    }
   
}

# Testing
# -------

# before_tests = "petroka_custom.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#   "frappe.desk.doctype.event.event.get_events": "petroka_custom.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#   "Task": "petroka_custom.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
auto_cancel_exempted_doctypes = [
	"Leave Ledger Entry",
    "Leave Allocation"
]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["petroka_custom.utils.before_request"]
# after_request = ["petroka_custom.utils.after_request"]

# Job Events
# ----------
# before_job = ["petroka_custom.utils.before_job"]
# after_job = ["petroka_custom.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#   {
#       "doctype": "{doctype_1}",
#       "filter_by": "{filter_by}",
#       "redact_fields": ["{field_1}", "{field_2}"],
#       "partial": 1,
#   },
#   {
#       "doctype": "{doctype_2}",
#       "filter_by": "{filter_by}",
#       "partial": 1,
#   },
#   {
#       "doctype": "{doctype_3}",
#       "strict": False,
#   },
#   {
#       "doctype": "{doctype_4}"
#   }
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#   "petroka_custom.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
#   "Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            ["Custom Field", "module", "=", "petroka_custom"]
        ]
    },
    {
        "doctype": "Client Script",
        "filters": [
            ["Client Script", "name", "=", "Zkteco Log List"]
        ]
    },
    {
        "doctype": "Custom HTML Block",
        "filters": [
            ["name", "in", [
                "Company Policy",
                "Events"
            ]]
        ]
    }
] 
