from petroka_custom.custom_script.patch_leave_application import apply_patch


def boot_session(bootinfo):
    print("🔥 BOOT SESSION CALLED")
    apply_patch()