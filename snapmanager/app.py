import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, GLib, Gdk
import threading
import subprocess
import shlex
import os


class SnapManagerApp(Gtk.Application):
    def _image_from_desktop(self, desktop_file_path):
        # Try to extract the Icon entry from the .desktop file
        if not desktop_file_path or not os.path.exists(desktop_file_path):
            return None
        icon_name = None
        try:
            with open(desktop_file_path, "r") as f:
                for line in f:
                    if line.strip().startswith("Icon="):
                        icon_name = line.strip().split("=", 1)[1]
                        break
        except Exception:
            return None
        if icon_name:
            img = self._image_from_icon_name(icon_name)
            if img:
                return img
        return None

    def __init__(self):
        super().__init__(application_id="com.example.SnapManager")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title("SnapManager (prototype)")
        self.window.set_default_size(900, 600)
        self._apply_css()

        header = Gtk.HeaderBar.new()
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_label = Gtk.Label(label="SnapManager — Prototype")
        title_label.set_xalign(0)
        title_box.append(title_label)

        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        popover = Gtk.Popover()
        pop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        pop_box.set_margin_top(6)
        pop_box.set_margin_bottom(6)
        pop_box.set_margin_start(6)
        pop_box.set_margin_end(6)
        btn_help = Gtk.Button(label="Help / Usage Tips")
        btn_help.connect("clicked", lambda w: self.show_help_dialog())
        pop_box.append(btn_help)
        btn_about = Gtk.Button(label="About SnapManager")
        btn_about.connect("clicked", lambda w: self.show_about_dialog())
        pop_box.append(btn_about)
        popover.set_child(pop_box)
        menu_btn.set_popover(popover)
        title_box.append(menu_btn)

        header.set_title_widget(title_box)
        self.window.set_titlebar(header)

        paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)

        # Left: snaps
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left_box.set_margin_top(6)
        left_box.set_margin_bottom(6)
        left_box.set_margin_start(6)
        left_box.set_margin_end(6)
        snap_label = Gtk.Label(label="Installed Snaps")
        snap_label.set_xalign(0)
        left_box.append(snap_label)

        snap_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_hold_all = Gtk.Button(label="Hold all snaps")
        btn_hold_all.connect(
            "clicked",
            lambda w: self.confirm_and_run_snap_hold(None, hold=True, duration=None),
        )
        snap_controls.append(btn_hold_all)

        btn_hold_all_24 = Gtk.Button(label="Hold all 24h")
        btn_hold_all_24.connect(
            "clicked",
            lambda w: self.confirm_and_run_snap_hold(None, hold=True, duration="24h"),
        )
        snap_controls.append(btn_hold_all_24)

        btn_unhold_all = Gtk.Button(label="Unhold all snaps")
        btn_unhold_all.connect(
            "clicked",
            lambda w: self.confirm_and_run_snap_hold(None, hold=False, duration=None),
        )
        snap_controls.append(btn_unhold_all)

        btn_hold_status = Gtk.Button(label="Show hold status")
        btn_hold_status.connect("clicked", lambda w: self.show_snap_refresh_status())
        snap_controls.append(btn_hold_status)

        left_box.append(snap_controls)

        snap_search = Gtk.Entry()
        snap_search.set_placeholder_text("Search snaps")
        snap_search.connect("changed", lambda w: self.set_snap_filter(w.get_text()))
        left_box.append(snap_search)

        self.snap_list = Gtk.ListBox()
        snap_scroll = Gtk.ScrolledWindow()
        snap_scroll.set_child(self.snap_list)
        snap_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        snap_scroll.set_hexpand(True)
        snap_scroll.set_vexpand(True)
        left_box.append(snap_scroll)

        refresh_snaps_btn = Gtk.Button(label="Refresh snaps")
        refresh_snaps_btn.connect("clicked", lambda w: self.populate_snaps())
        left_box.append(refresh_snaps_btn)

        # Right: apt packages
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right_box.set_margin_top(6)
        right_box.set_margin_bottom(6)
        right_box.set_margin_start(6)
        right_box.set_margin_end(6)
        apt_label = Gtk.Label(label="Installed apt packages")
        apt_label.set_xalign(0)
        right_box.append(apt_label)

        apt_search = Gtk.Entry()
        apt_search.set_placeholder_text("Search apt packages")
        apt_search.connect("changed", lambda w: self.set_apt_filter(w.get_text()))
        right_box.append(apt_search)

        self.apt_list = Gtk.ListBox()
        apt_scroll = Gtk.ScrolledWindow()
        apt_scroll.set_child(self.apt_list)
        apt_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        apt_scroll.set_hexpand(True)
        apt_scroll.set_vexpand(True)
        right_box.append(apt_scroll)

        refresh_apt_btn = Gtk.Button(label="Refresh apt list")
        refresh_apt_btn.connect("clicked", lambda w: self.populate_apt())
        right_box.append(refresh_apt_btn)

        paned.set_start_child(left_box)
        paned.set_end_child(right_box)

        self.window.set_child(paned)
        self.snap_items = []
        self.apt_items = []
        self.snap_filter = ""
        self.apt_filter = ""
        self.snap_hold_status = {}
        self.populate_snaps()
        self.populate_apt()
        self.window.show()

    def run_command(self, cmd, use_shell=False, capture_output=True):
        try:
            if capture_output:
                result = subprocess.run(
                    cmd if use_shell else shlex.split(cmd),
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=use_shell,
                )
                return result.returncode, result.stdout, result.stderr
            else:
                p = subprocess.Popen(cmd if use_shell else shlex.split(cmd))
                p.wait()
                return p.returncode, "", ""
        except FileNotFoundError as e:
            return 127, "", str(e)

    def populate_snaps(self):
        self.clear_listbox(self.snap_list)

        code, out, err = self.run_command("snap list")
        if code != 0:
            row = Gtk.Label(label=f"Error listing snaps: {err or out}")
            self.snap_list.append(row)
            return

        lines = out.strip().splitlines()
        if len(lines) <= 1:
            self.snap_list.append(Gtk.Label(label="No snaps found."))
            return

        self.snap_items = []
        seen = set()
        # header line at 0
        for ln in lines[1:]:
            parts = [p for p in ln.split() if p]
            if not parts:
                continue
            name = parts[0]
            if name in seen:
                continue
            seen.add(name)
            version = parts[1] if len(parts) > 1 else ""
            publisher = parts[2] if len(parts) > 2 else ""
            self.snap_items.append(
                {"name": name, "version": version, "publisher": publisher}
            )
        self.snap_hold_status = {item["name"]: "…" for item in self.snap_items}
        self.render_snaps()
        threading.Thread(target=self._load_snap_holds, daemon=True).start()

    def render_snaps(self):
        self.clear_listbox(self.snap_list)
        items = [
            i for i in self.snap_items if self.snap_filter.lower() in i["name"].lower()
        ]

        if not items:
            msg = "No snaps match your search." if self.snap_filter else "No snaps available."
            self.snap_list.append(Gtk.Label(label=msg))
            return

        for item in items:
            name = item["name"]
            version = item["version"]
            publisher = item["publisher"]
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            icon = self._icon_for_snap(name)
            row_box.append(icon)

            label = Gtk.Label(label=f"{name} — {version} — {publisher}")
            label.set_xalign(0)
            row_box.append(label)

            hold_lbl = Gtk.Label(label=f"Hold: {self.snap_hold_status.get(name, '…')}")
            hold_lbl.set_xalign(0)
            row_box.append(hold_lbl)

            # Add Snap Problem Solver button
            btn_solver = Gtk.Button(label="Snap Problem Solver")
            btn_solver.connect(
                "clicked", lambda w, n=name: self.show_snap_problem_solver(n)
            )
            row_box.append(btn_solver)

            hbox.append(row_box)

            btn_hold_snap = Gtk.Button(label="Hold updates")
            btn_hold_snap.connect(
                "clicked",
                lambda w, n=name: self.confirm_and_run_snap_hold(
                    n, hold=True, duration=None
                ),
            )
            hbox.append(btn_hold_snap)

            btn_hold_snap_24 = Gtk.Button(label="Hold 24h")
            btn_hold_snap_24.connect(
                "clicked",
                lambda w, n=name: self.confirm_and_run_snap_hold(
                    n, hold=True, duration="24h"
                ),
            )
            hbox.append(btn_hold_snap_24)

            btn_unhold_snap = Gtk.Button(label="Unhold")
            btn_unhold_snap.connect(
                "clicked",
                lambda w, n=name: self.confirm_and_run_snap_hold(
                    n, hold=False, duration=None
                ),
            )
            hbox.append(btn_unhold_snap)

            btn_run_unsandbox = Gtk.Button(label="Run unsandboxed")
            btn_run_unsandbox.connect(
                "clicked", lambda w, n=name: self.confirm_and_run_snap_dev(n)
            )
            hbox.append(btn_run_unsandbox)

            btn_switch_apt = Gtk.Button(label="Switch to apt")
            btn_switch_apt.connect(
                "clicked", lambda w, n=name: self.suggest_switch_to_apt(n)
            )
            hbox.append(btn_switch_apt)

            self.snap_list.append(hbox)

    def show_snap_problem_solver(self, snap_name: str):
        # Diagnostic dialog - ask what's wrong and run probes
        dialog = Gtk.Dialog(
            title=f"Snap Problem Solver: {snap_name}",
            transient_for=self.window,
            modal=True,
        )
        dialog.maximize()
        box = dialog.get_content_area()
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)
        box.append(vbox)

        intro = Gtk.Label(
            label=f"Let's diagnose the issue with {snap_name}.\n\nWhat's happening?"
        )
        intro.set_wrap(True)
        intro.set_xalign(0)
        vbox.append(intro)

        # Question buttons
        questions = [
            ("App won't start", "crash"),
            ("App starts but can't access files", "files"),
            ("App can't access network", "network"),
            ("App can't access microphone/camera", "devices"),
            ("App works but is slow/buggy", "performance"),
            ("Other/Unknown issue", "unknown"),
        ]

        for q_text, q_type in questions:
            btn = Gtk.Button(label=q_text)
            btn.connect("clicked", lambda w, t=q_type: self._run_diagnostics(snap_name, t, dialog))
            vbox.append(btn)

        btn_close = Gtk.Button(label="Cancel")
        btn_close.connect("clicked", lambda b: dialog.destroy())
        vbox.append(btn_close)
        dialog.show()

    def _run_diagnostics(self, snap_name: str, issue_type: str, prev_dialog):
        prev_dialog.destroy()

        # Run and parse diagnostics for user-friendly summary
        info_code, info_out, info_err = self.run_command(f"snap info {shlex.quote(snap_name)}")
        connections_code, connections_out, connections_err = self.run_command(f"snap connections {shlex.quote(snap_name)}")
        apt_code, apt_out, apt_err = self.run_command(f"apt-cache search {shlex.quote(snap_name)}")

        # Parse classic support
        supports_classic = ("classic" in info_out.lower()) if info_code == 0 else False
        # Parse plugs
        has_file_plug = "home" in connections_out or "removable-media" in connections_out
        has_network_plug = "network" in connections_out or "network-bind" in connections_out
        has_audio_plug = any(x in connections_out for x in ["audio-record", "camera", "microphone"])
        # Parse apt availability
        apt_available = snap_name.lower() in apt_out.lower() if apt_code == 0 else False

        diagnostics = {
            "supports_classic": supports_classic,
            "has_plugs": has_file_plug or has_network_plug or has_audio_plug,
            "apt_available": apt_available,
        }

        # Build user-friendly summary
        summary_lines = []
        if info_code != 0:
            summary_lines.append("Could not get snap info.")
        else:
            if supports_classic:
                summary_lines.append("Classic mode is available for this snap (can run with fewer restrictions).")
            else:
                summary_lines.append("Classic mode is NOT available for this snap.")
        if connections_code != 0:
            summary_lines.append("Could not get snap connections.")
        else:
            if has_file_plug:
                summary_lines.append("Snap has file access plugs (home/removable-media).")
            else:
                summary_lines.append("Snap does NOT have file access plugs (may not access your files).")
            if has_network_plug:
                summary_lines.append("Snap has network access plugs.")
            else:
                summary_lines.append("Snap does NOT have network access plugs.")
            if has_audio_plug:
                summary_lines.append("Snap has audio/camera plugs.")
            else:
                summary_lines.append("Snap does NOT have audio/camera plugs.")
        if apt_code != 0:
            summary_lines.append("Could not check for APT package.")
        else:
            if apt_available:
                summary_lines.append("An APT package with this name is available.")
            else:
                summary_lines.append("No APT package with this name found.")

        # Recommend solution based on issue type and diagnostics
        recommendation = self._recommend_solution(snap_name, issue_type, diagnostics)

        # Severity mapping
        severity_map = {
            "crash": ("Critical", "#d32f2f"),
            "files": ("Warning", "#fbc02d"),
            "network": ("Warning", "#fbc02d"),
            "devices": ("Warning", "#fbc02d"),
            "performance": ("Info", "#1976d2"),
            "unknown": ("Info", "#1976d2"),
        }
        severity, sev_color = severity_map.get(issue_type, ("Info", "#1976d2"))

        dialog = Gtk.Dialog(
            title=f"Recommended Solution for {snap_name}",
            transient_for=self.window,
            modal=True,
        )
        dialog.set_default_size(400, 320)
        box = dialog.get_content_area()

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        box.append(scroll)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_top(6)
        vbox.set_margin_bottom(6)
        vbox.set_margin_start(6)
        vbox.set_margin_end(6)
        vbox.set_hexpand(True)
        vbox.set_vexpand(True)
        scroll.set_child(vbox)

        # Severity indicator
        sev_lbl = Gtk.Label(label=f"Severity: {severity}")
        sev_lbl.set_wrap(False)
        sev_lbl.set_xalign(0)
        sev_lbl.set_hexpand(True)
        sev_lbl.set_vexpand(False)
        sev_lbl.set_margin_bottom(2)
        sev_lbl.set_markup(f"<b><span foreground=\"{sev_color}\">Severity: {severity}</span></b>")
        vbox.append(sev_lbl)

        # Issue summary
        issue_map = {
            "crash": "App won't start",
            "files": "Can't access files",
            "network": "Can't access network",
            "devices": "Can't access microphone/camera",
            "performance": "Performance issues",
            "unknown": "Unknown issue",
        }
        summary = Gtk.Label(label=f"Issue: {issue_map.get(issue_type, issue_type)}")
        summary.set_wrap(True)
        summary.set_xalign(0)
        summary.set_hexpand(True)
        summary.set_vexpand(False)
        vbox.append(summary)

        # User-friendly diagnostic summary
        diag_summary = Gtk.Label(label="\n".join(summary_lines))
        diag_summary.set_wrap(True)
        diag_summary.set_xalign(0)
        diag_summary.set_hexpand(True)
        diag_summary.set_vexpand(False)
        diag_summary.set_margin_bottom(6)
        vbox.append(diag_summary)

        # Recommendation
        rec_lbl = Gtk.Label(label=recommendation["title"])
        rec_lbl.get_style_context().add_class("title-2")
        rec_lbl.set_wrap(True)
        rec_lbl.set_xalign(0)
        rec_lbl.set_hexpand(True)
        rec_lbl.set_vexpand(False)
        vbox.append(rec_lbl)

        # Why this solution
        why = Gtk.Label(label=recommendation["why"])
        why.set_wrap(True)
        why.set_xalign(0)
        why.set_hexpand(True)
        why.set_vexpand(True)
        vbox.append(why)


        # Apply button
        btn_apply = Gtk.Button(label=f"Apply: {recommendation['title']}")
        btn_apply.get_style_context().add_class("suggested-action")
        btn_apply.connect("clicked", lambda w: (recommendation["action"](snap_name), dialog.destroy()))
        vbox.append(btn_apply)

        btn_close = Gtk.Button(label="Close")
        btn_close.connect("clicked", lambda b: dialog.destroy())
        vbox.append(btn_close)
        dialog.show()

    def _check_classic_support(self, snap_name: str) -> bool:
        code, out, _ = self.run_command(f"snap info {shlex.quote(snap_name)}")
        return "classic" in out.lower() if code == 0 else False

    def _check_snap_plugs(self, snap_name: str) -> bool:
        code, out, _ = self.run_command(f"snap connections {shlex.quote(snap_name)}")
        return "plug" in out.lower() if code == 0 else False

    def _check_apt_package(self, snap_name: str) -> bool:
        code, out, _ = self.run_command(f"apt-cache search {shlex.quote(snap_name)}")
        return snap_name.lower() in out.lower() if code == 0 else False

    def _recommend_solution(self, snap_name: str, issue_type: str, diagnostics: dict) -> dict:
        # Auto-recommend based on issue type and diagnostics
        
        if issue_type == "crash":
            if diagnostics["supports_classic"]:
                return {
                    "title": "Try Classic Confinement",
                    "why": "Classic mode removes sandbox restrictions that might cause crashes.",
                    "action": lambda n: self.run_long_command(
                        f"Install {n} with classic confinement",
                        f"snap install --classic {shlex.quote(n)}"
                    ),
                }
            else:
                return {
                    "title": "Try Developer Mode (Devmode)",
                    "why": "Devmode removes all sandbox restrictions. Good for testing.",
                    "action": lambda n: self._confirm_devmode_install(n),
                }
        
        elif issue_type == "files":
            if diagnostics["has_plugs"]:
                return {
                    "title": "Connect File Access Permissions",
                    "why": "The snap needs permission to access files. We'll show available plugs.",
                    "action": lambda n: self.run_long_command(
                        f"Show available connections for {n}",
                        f"snap connections {shlex.quote(n)}"
                    ),
                }
            else:
                return {
                    "title": "Switch to APT Version",
                    "why": "No file plugs available. Using APT version avoids sandbox entirely.",
                    "action": lambda n: self.run_long_command(
                        f"Install {n} from APT",
                        f"apt install {shlex.quote(n)}"
                    ),
                }
        
        elif issue_type == "network":
            return {
                "title": "Connect Network Permission",
                "why": "The snap needs network access plug. Let's check available connections.",
                "action": lambda n: self.run_long_command(
                    f"Show network-related connections for {n}",
                    f"snap connections {shlex.quote(n)} | grep -i network || snap connections {shlex.quote(n)}"
                ),
            }
        
        elif issue_type == "devices":
            return {
                "title": "Connect Camera/Microphone Permission",
                "why": "The snap needs hardware device access. Let's check available plugs.",
                "action": lambda n: self.run_long_command(
                    f"Show device connections for {n}",
                    f"snap connections {shlex.quote(n)} | grep -i -E 'camera|audio|microphone' || snap connections {shlex.quote(n)}"
                ),
            }
        
        elif issue_type == "performance":
            if diagnostics["apt_available"]:
                return {
                    "title": "Switch to APT (Faster Alternative)",
                    "why": "APT packages typically have less overhead than snaps.",
                    "action": lambda n: self.run_long_command(
                        f"Install {n} from APT",
                        f"apt install {shlex.quote(n)}"
                    ),
                }
            else:
                return {
                    "title": "Try Developer Mode",
                    "why": "Devmode removes confinement overhead that may be slowing the app.",
                    "action": lambda n: self._confirm_devmode_install(n),
                }
        
        else:  # unknown
            return {
                "title": "Check Snap Connections & Info",
                "why": "Let's check the snap's configuration and available permissions.",
                "action": lambda n: self.run_long_command(
                    f"Show detailed info and connections for {n}",
                    f"snap info {shlex.quote(n)} && echo '\n--- Connections ---' && snap connections {shlex.quote(n)}"
                ),
            }

    def _confirm_devmode_install(self, snap_name: str):
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=f"Install {snap_name} in devmode?\n\nThis removes all sandbox restrictions. Proceed only if you trust this snap.",
        )
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("Install Devmode", Gtk.ResponseType.OK)
        resp = self._run_dialog_blocking(dlg)
        if resp == Gtk.ResponseType.OK:
            cmd = f"snap remove {shlex.quote(snap_name)} && snap install --devmode {shlex.quote(snap_name)}"
            self.run_long_command(f"Reinstall {snap_name} in devmode", cmd)

    def populate_apt(self):
        self.clear_listbox(self.apt_list)

        code, out, err = self.run_command("apt list --installed")
        if code != 0:
            row = Gtk.Label(label=f"Error listing apt packages: {err or out}")
            self.apt_list.append(row)
            return

        lines = out.strip().splitlines()
        seen = set()
        self.apt_items = []
        # first line may be 'Listing...'
        for ln in lines:
            if "/" not in ln:
                continue
            pkg = ln.split("/")[0]
            if pkg in seen:
                continue
            seen.add(pkg)
            self.apt_items.append(pkg)
        if not self.apt_items:
            self.apt_list.append(Gtk.Label(label="No apt packages found."))
            return
        self.render_apt()

    def render_apt(self):
        self.clear_listbox(self.apt_list)
        items = [p for p in self.apt_items if self.apt_filter.lower() in p.lower()]
        if not items:
            msg = "No apt packages match your search." if self.apt_filter else "No apt packages available."
            self.apt_list.append(Gtk.Label(label=msg))
            return
        for pkg in items:
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            icon = self._icon_for_package(pkg)
            row_box.append(icon)

            label = Gtk.Label(label=pkg)
            label.set_xalign(0)
            row_box.append(label)

            hbox.append(row_box)

            # Show details button
            btn_details = Gtk.Button(label="Show details")
            btn_details.connect("clicked", lambda w, n=pkg: self.show_apt_details(n))
            hbox.append(btn_details)

            # Remove package button
            btn_remove = Gtk.Button(label="Remove")
            btn_remove.connect("clicked", lambda w, n=pkg: self.confirm_and_remove_apt(n))
            hbox.append(btn_remove)

            # Reinstall package button
            btn_reinstall = Gtk.Button(label="Reinstall")
            btn_reinstall.connect("clicked", lambda w, n=pkg: self.confirm_and_reinstall_apt(n))
            hbox.append(btn_reinstall)

            self.apt_list.append(hbox)
    def show_apt_details(self, pkg):
        code, out, err = self.run_command(f"apt show {shlex.quote(pkg)}")
        txt = out.strip() or err.strip() or f"return code {code}"
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=f"APT package details for {pkg}:",
        )
        dlg.format_secondary_text(txt)
        self._run_dialog_blocking(dlg)

    def confirm_and_remove_apt(self, pkg):
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=f"Remove {pkg}?\n\nThis will run 'sudo apt remove {pkg}'. Proceed?",
        )
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("Remove", Gtk.ResponseType.OK)
        resp = self._run_dialog_blocking(dlg)
        if resp == Gtk.ResponseType.OK:
            cmd = f"sudo apt remove {shlex.quote(pkg)}"
            self.run_long_command(f"Remove {pkg}", cmd)

    def confirm_and_reinstall_apt(self, pkg):
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=f"Reinstall {pkg}?\n\nThis will run 'sudo apt install --reinstall {pkg}'. Proceed?",
        )
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("Reinstall", Gtk.ResponseType.OK)
        resp = self._run_dialog_blocking(dlg)
        if resp == Gtk.ResponseType.OK:
            cmd = f"sudo apt install --reinstall {shlex.quote(pkg)}"
            self.run_long_command(f"Reinstall {pkg}", cmd)

    def set_snap_filter(self, text: str):
        self.snap_filter = text or ""
        self.render_snaps()

    def set_apt_filter(self, text: str):
        self.apt_filter = text or ""
        self.render_apt()

    def show_snap_refresh_status(self):
        code, out, err = self.run_command("snap refresh --time")
        txt = out or err or f"return code {code}"
        self.show_info("Snap refresh status", code, txt, "")

    def confirm_and_run_apt_mark(self, pkg, hold=True):
        action = "hold" if hold else "unhold"
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=f"{action.title()} {pkg}?\n\nThis will run `sudo apt-mark {action} {pkg}`. Proceed?",
        )
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("Run", Gtk.ResponseType.OK)
        resp = self._run_dialog_blocking(dlg)
        if resp == Gtk.ResponseType.OK:
            cmd = f"sudo apt-mark {action} {shlex.quote(pkg)}"
            # attempt to run with pkexec first
            self.run_long_command(f"apt-mark {action} {pkg}", cmd)

    def confirm_and_run_snap_dev(self, snap_name):
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=(
                f"Attempt unsandboxed run for {snap_name}?\n\n"
                "This will attempt to reinstall the snap with relaxed confinement (`--devmode`). "
                "Many store snaps cannot be installed this way. This action is potentially unsafe. Proceed?"
            ),
        )
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("Reinstall --devmode", Gtk.ResponseType.OK)
        resp = self._run_dialog_blocking(dlg)
        if resp == Gtk.ResponseType.OK:
            # remove and reinstall with --devmode (may fail for store snaps)
            cmd = f"sudo snap remove {shlex.quote(snap_name)} && sudo snap install --devmode {shlex.quote(snap_name)}"
            self.run_long_command(f"Reinstall --devmode {snap_name}", cmd)

    def suggest_switch_to_apt(self, snap_name):
        # Show a dialog suggesting apt install command
        pkg = snap_name  # naive mapping
        cmd = f"sudo apt install {pkg}"
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=(
                f"Switch {snap_name} to apt?\n\n"
                f"If an apt package exists for this app, running `{cmd}` will install the apt version. "
                f"You may then remove the snap with `sudo snap remove {snap_name}`."
            ),
        )
        resp = self._run_dialog_blocking(dlg)
        if resp == Gtk.ResponseType.OK:
            self.run_long_command(f"apt install {pkg}", cmd)

    def confirm_and_run_snap_hold(self, snap_name, hold=True, duration=None):
        flag = "--hold" if hold else "--unhold"
        duration_part = f"={duration}" if duration and hold else ""
        target = snap_name if snap_name else "all snaps"
        cmd = f"snap refresh {flag}{duration_part}"
        if snap_name:
            cmd = f"{cmd} {shlex.quote(snap_name)}"

        action = "hold updates" if hold else "unhold updates"
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=(
                f"{action.title()} for {target}?\n\n"
                f"This will run `{cmd}`. Auto-refresh holds stop automatic updates; "
                f"targeted refreshes like `snap refresh {snap_name or '<snap>'}` can still proceed."
            ),
        )
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("Run", Gtk.ResponseType.OK)
        resp = self._run_dialog_blocking(dlg)
        if resp == Gtk.ResponseType.OK:
            self.run_long_command(f"snap refresh {flag} {target}", cmd)

    def show_info(self, title, code, out, err):
        typ = "Success" if code == 0 else "Error"
        txt = out.strip() or err.strip() or f"return code {code}"
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=f"{title}: {typ}\n\n{txt}",
        )
        self._run_dialog_blocking(dlg)

    def show_help_dialog(self):
        tips = (
            "How to use SnapManager:\n"
            "• Snap actions: hold/unhold updates, run unsandboxed (devmode), switch to apt.\n"
            "• Apt actions: show details, remove, reinstall.\n"
            "• Snap Problem Solver: pick the issue, read the recommended fix, and click Apply.\n"
            "Safety: risky actions (devmode/unsandboxed) prompt before running."
        )
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Help / Usage Tips",
        )
        dlg.set_property("secondary-text", tips)
        self._run_dialog_blocking(dlg)

    def show_about_dialog(self):
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="SnapManager Prototype",
        )
        dlg.set_property(
            "secondary-text",
            "A GTK4 helper for managing snaps and apt packages on Ubuntu.\n"
            "Shows safe commands, prompts before risky actions, and provides quick fixes for common snap issues.",
        )
        self._run_dialog_blocking(dlg)

    def _icon_for_snap(self, name: str) -> Gtk.Image:
        # 1) Try to find a desktop file in common Ubuntu locations
        desktop_paths = [
            os.path.expanduser("~/.local/share/applications"),
            "/usr/share/applications",
            "/var/lib/snapd/desktop/applications",
        ]
        desk = self._find_desktop_file(name, desktop_paths)
        if desk:
            img = self._image_from_desktop(desk)
            if img:
                return img

        # 2) Common snap icon paths
        icon_paths = [
            f"/var/lib/snapd/desktop/icons/{name}.png",
            f"/var/lib/snapd/desktop/icons/{name}.svg",
            f"/snap/{name}/current/meta/gui/icon.png",
            f"/snap/{name}/current/meta/gui/icon.svg",
        ]
        for p in icon_paths:
            if os.path.exists(p):
                img = Gtk.Image.new_from_file(p)
                if img.get_paintable():
                    return img

        # 3) Theme lookups with common icon names
        for icon_name in [name, f"{name}-symbolic", f"{name}.icon", f"snap.{name}"]:
            img = self._image_from_icon_name(icon_name)
            if img:
                return img

        # 4) Fallback
        return Gtk.Image.new_from_icon_name("application-x-executable")

    def _icon_for_package(self, name: str) -> Gtk.Image:
        # Try to find a desktop file in more locations for apt packages
        desktop_paths = [
            os.path.expanduser("~/.local/share/applications"),
            "/usr/share/applications",
            "/var/lib/snapd/desktop/applications",
        ]
        desk = self._find_desktop_file(name, desktop_paths)
        if desk:
            img = self._image_from_desktop(desk)
            if img:
                return img
        img = self._image_from_icon_name(name)
        if img:
            return img
        return Gtk.Image.new_from_icon_name("application-x-executable")

    def clear_listbox(self, listbox: Gtk.ListBox):
        child = listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            listbox.remove(child)
            child = next_child

    def _apply_css(self):
        css = b"""
        window {
            background: #1c1c1c;
            color: #e6e6e6;
        }
        headerbar {
            background: #242424;
            color: #e6e6e6;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _set_dialog_secondary(self, dialog: Gtk.MessageDialog, text: str):
        # Deprecated helper kept for compatibility; not used after inlined text approach.
        dialog.set_property("text", f"{dialog.get_property('text')}\n\n{text}")

    def _run_dialog_blocking(self, dialog: Gtk.MessageDialog):
        response_holder = {"resp": None}

        def on_response(dlg, resp):
            response_holder["resp"] = resp
            dlg.hide()
            loop.quit()

        loop = GLib.MainLoop()
        dialog.connect("response", on_response)
        dialog.present()
        loop.run()
        dialog.destroy()
        return response_holder["resp"]

    def run_long_command(self, title: str, cmd: str):
        dialog = Gtk.Dialog(title=title, transient_for=self.window, modal=True)
        dialog.set_default_size(500, 220)

        box = dialog.get_content_area()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        vbox.set_margin_start(8)
        vbox.set_margin_end(8)
        box.append(vbox)

        lbl = Gtk.Label(label=f"Running: {cmd}")
        lbl.set_xalign(0)
        lbl.set_wrap(True)
        vbox.append(lbl)

        spinner = Gtk.Spinner()
        spinner.set_spinning(True)
        vbox.append(spinner)

        output_view = Gtk.TextView()
        output_view.set_editable(False)
        output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        output_buf = output_view.get_buffer()
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(output_view)
        vbox.append(scroll)

        btn_close = Gtk.Button(label="Close")
        btn_close.set_sensitive(False)
        btn_close.connect("clicked", lambda b: dialog.destroy())
        vbox.append(btn_close)

        dialog.show()

        def append_text(text):
            GLib.idle_add(lambda: output_buf.insert(output_buf.get_end_iter(), text))

        def worker():
            full_cmd = cmd
            if shutil_which("pkexec"):
                full_cmd = f"pkexec bash -c {shlex.quote(cmd)}"
            proc = subprocess.Popen(
                full_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in proc.stdout:
                append_text(line)
            proc.wait()
            rc = proc.returncode
            GLib.idle_add(self._finish_long_command, dialog, spinner, btn_close, rc)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_long_command(self, dialog, spinner, btn_close, rc):
        spinner.set_spinning(False)
        btn_close.set_sensitive(True)
        dialog.set_title(f"{dialog.get_title()} — done (rc={rc})")
        return False

    def _find_desktop_file(self, name: str, paths):
        candidates = [name, f"{name}.desktop", f"{name}.desktop.desktop"]
        for path in paths:
            for candidate in candidates:
                full_path = os.path.join(path, candidate)
                if os.path.exists(full_path):
                    return full_path
        return None

    def _image_from_icon_name(self, icon_name: str):
        if not icon_name:
            return None
        # Simplify: rely on icon name lookup and theme resolution via Gtk.Image
        img = Gtk.Image.new_from_icon_name(icon_name)
        if img.get_paintable():
            return img
        return None

    def _load_snap_holds(self):
        for item in list(self.snap_items):
            name = item["name"]
            code, out, err = self.run_command(
                f"snap refresh --time {shlex.quote(name)}"
            )
            status = self._parse_snap_hold(out or err or "", code)
            self.snap_hold_status[name] = status
            GLib.idle_add(self.render_snaps)

    def _parse_snap_hold(self, text: str, code: int) -> str:
        if code != 0:
            return "unknown"
        for line in text.splitlines():
            lower = line.lower()
            if "hold" in lower:
                return line.strip()
        return "none"


def shutil_which(cmd):
    from shutil import which

    return which(cmd) is not None
