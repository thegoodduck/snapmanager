import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gio', '2.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gio, Gtk, GLib, Gdk
import threading
import subprocess
import shlex
import sys

class SnapManagerApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='com.example.SnapManager')
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title('SnapManager (prototype)')
        self.window.set_default_size(900, 600)
        self._apply_css()

        header = Gtk.HeaderBar.new()
        header.set_title_widget(Gtk.Label(label='SnapManager — Prototype'))
        self.window.set_titlebar(header)

        paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)

        # Left: snaps
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left_box.set_margin_top(6)
        left_box.set_margin_bottom(6)
        left_box.set_margin_start(6)
        left_box.set_margin_end(6)
        snap_label = Gtk.Label(label='Installed Snaps')
        snap_label.set_xalign(0)
        left_box.append(snap_label)

        snap_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_hold_all = Gtk.Button(label='Hold all snaps')
        btn_hold_all.connect('clicked', lambda w: self.confirm_and_run_snap_hold(None, hold=True, duration=None))
        snap_controls.append(btn_hold_all)

        btn_hold_all_24 = Gtk.Button(label='Hold all 24h')
        btn_hold_all_24.connect('clicked', lambda w: self.confirm_and_run_snap_hold(None, hold=True, duration='24h'))
        snap_controls.append(btn_hold_all_24)

        btn_unhold_all = Gtk.Button(label='Unhold all snaps')
        btn_unhold_all.connect('clicked', lambda w: self.confirm_and_run_snap_hold(None, hold=False, duration=None))
        snap_controls.append(btn_unhold_all)

        left_box.append(snap_controls)

        self.snap_list = Gtk.ListBox()
        snap_scroll = Gtk.ScrolledWindow()
        snap_scroll.set_child(self.snap_list)
        snap_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        snap_scroll.set_hexpand(True)
        snap_scroll.set_vexpand(True)
        left_box.append(snap_scroll)

        refresh_snaps_btn = Gtk.Button(label='Refresh snaps')
        refresh_snaps_btn.connect('clicked', lambda w: self.populate_snaps())
        left_box.append(refresh_snaps_btn)

        # Right: apt packages
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right_box.set_margin_top(6)
        right_box.set_margin_bottom(6)
        right_box.set_margin_start(6)
        right_box.set_margin_end(6)
        apt_label = Gtk.Label(label='Installed apt packages')
        apt_label.set_xalign(0)
        right_box.append(apt_label)

        self.apt_list = Gtk.ListBox()
        apt_scroll = Gtk.ScrolledWindow()
        apt_scroll.set_child(self.apt_list)
        apt_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        apt_scroll.set_hexpand(True)
        apt_scroll.set_vexpand(True)
        right_box.append(apt_scroll)

        refresh_apt_btn = Gtk.Button(label='Refresh apt list')
        refresh_apt_btn.connect('clicked', lambda w: self.populate_apt())
        right_box.append(refresh_apt_btn)

        paned.set_start_child(left_box)
        paned.set_end_child(right_box)

        self.window.set_child(paned)
        self.populate_snaps()
        self.populate_apt()
        self.window.show()

    def run_command(self, cmd, use_shell=False, capture_output=True):
        try:
            if capture_output:
                result = subprocess.run(cmd if use_shell else shlex.split(cmd), check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=use_shell)
                return result.returncode, result.stdout, result.stderr
            else:
                p = subprocess.Popen(cmd if use_shell else shlex.split(cmd))
                p.wait()
                return p.returncode, '', ''
        except FileNotFoundError as e:
            return 127, '', str(e)

    def populate_snaps(self):
        self.clear_listbox(self.snap_list)

        code, out, err = self.run_command('snap list --all')
        if code != 0:
            row = Gtk.Label(label=f'Error listing snaps: {err or out}')
            self.snap_list.append(row)
            return

        lines = out.strip().splitlines()
        if len(lines) <= 1:
            return

        # header line at 0
        for ln in lines[1:]:
            parts = [p for p in ln.split() if p]
            if not parts:
                continue
            name = parts[0]
            version = parts[1] if len(parts) > 1 else ''
            publisher = parts[2] if len(parts) > 2 else ''
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            label = Gtk.Label(label=f'{name} — {version} — {publisher}')
            label.set_xalign(0)
            hbox.append(label)

            btn_hold_snap = Gtk.Button(label='Hold updates')
            btn_hold_snap.connect('clicked', lambda w, n=name: self.confirm_and_run_snap_hold(n, hold=True, duration=None))
            hbox.append(btn_hold_snap)

            btn_hold_snap_24 = Gtk.Button(label='Hold 24h')
            btn_hold_snap_24.connect('clicked', lambda w, n=name: self.confirm_and_run_snap_hold(n, hold=True, duration='24h'))
            hbox.append(btn_hold_snap_24)

            btn_unhold_snap = Gtk.Button(label='Unhold')
            btn_unhold_snap.connect('clicked', lambda w, n=name: self.confirm_and_run_snap_hold(n, hold=False, duration=None))
            hbox.append(btn_unhold_snap)

            btn_run_unsandbox = Gtk.Button(label='Run unsandboxed')
            btn_run_unsandbox.connect('clicked', lambda w, n=name: self.confirm_and_run_snap_dev(n))
            hbox.append(btn_run_unsandbox)

            btn_switch_apt = Gtk.Button(label='Switch to apt')
            btn_switch_apt.connect('clicked', lambda w, n=name: self.suggest_switch_to_apt(n))
            hbox.append(btn_switch_apt)

            self.snap_list.append(hbox)

    def populate_apt(self):
        self.clear_listbox(self.apt_list)

        code, out, err = self.run_command('apt list --installed')
        if code != 0:
            row = Gtk.Label(label=f'Error listing apt packages: {err or out}')
            self.apt_list.append(row)
            return

        lines = out.strip().splitlines()
        # first line may be 'Listing...'
        for ln in lines:
            if '/' not in ln:
                continue
            pkg = ln.split('/')[0]
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            label = Gtk.Label(label=pkg)
            label.set_xalign(0)
            hbox.append(label)

            btn_hold = Gtk.Button(label='Hold')
            btn_hold.connect('clicked', lambda w, p=pkg: self.confirm_and_run_apt_mark(p, hold=True))
            hbox.append(btn_hold)

            btn_unhold = Gtk.Button(label='Unhold')
            btn_unhold.connect('clicked', lambda w, p=pkg: self.confirm_and_run_apt_mark(p, hold=False))
            hbox.append(btn_unhold)

            self.apt_list.append(hbox)

    def confirm_and_run_apt_mark(self, pkg, hold=True):
        action = 'hold' if hold else 'unhold'
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=f'{action.title()} {pkg}?\n\nThis will run `sudo apt-mark {action} {pkg}`. Proceed?'
        )
        dlg.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dlg.add_button('Run', Gtk.ResponseType.OK)
        resp = self._run_dialog_blocking(dlg)
        if resp == Gtk.ResponseType.OK:
            cmd = f"sudo apt-mark {action} {shlex.quote(pkg)}"
            # attempt to run with pkexec first
            self.run_long_command(f'apt-mark {action} {pkg}', cmd)

    def confirm_and_run_snap_dev(self, snap_name):
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=(
                f'Attempt unsandboxed run for {snap_name}?\n\n'
                'This will attempt to reinstall the snap with relaxed confinement (`--devmode`). '
                'Many store snaps cannot be installed this way. This action is potentially unsafe. Proceed?'
            )
        )
        dlg.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dlg.add_button('Reinstall --devmode', Gtk.ResponseType.OK)
        resp = self._run_dialog_blocking(dlg)
        if resp == Gtk.ResponseType.OK:
            # remove and reinstall with --devmode (may fail for store snaps)
            cmd = f"sudo snap remove {shlex.quote(snap_name)} && sudo snap install --devmode {shlex.quote(snap_name)}"
            self.run_long_command(f'Reinstall --devmode {snap_name}', cmd)

    def suggest_switch_to_apt(self, snap_name):
        # Show a dialog suggesting apt install command
        pkg = snap_name  # naive mapping
        cmd = f'sudo apt install {pkg}'
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=(
                f'Switch {snap_name} to apt?\n\n'
                f'If an apt package exists for this app, running `{cmd}` will install the apt version. '
                f'You may then remove the snap with `sudo snap remove {snap_name}`.'
            )
        )
        resp = self._run_dialog_blocking(dlg)
        if resp == Gtk.ResponseType.OK:
            self.run_long_command(f'apt install {pkg}', cmd)

    def confirm_and_run_snap_hold(self, snap_name, hold=True, duration=None):
        flag = '--hold' if hold else '--unhold'
        duration_part = f'={duration}' if duration and hold else ''
        target = snap_name if snap_name else 'all snaps'
        cmd = f"snap refresh {flag}{duration_part}"
        if snap_name:
            cmd = f"{cmd} {shlex.quote(snap_name)}"

        action = 'hold updates' if hold else 'unhold updates'
        timing = f' for {duration}' if duration else ''
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=(
                f'{action.title()} for {target}?\n\n'
                f'This will run `{cmd}`. Auto-refresh holds stop automatic updates; '
                f'targeted refreshes like `snap refresh {snap_name or "<snap>"}` can still proceed.'
            )
        )
        dlg.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dlg.add_button('Run', Gtk.ResponseType.OK)
        resp = self._run_dialog_blocking(dlg)
        if resp == Gtk.ResponseType.OK:
            self.run_long_command(f'snap refresh {flag} {target}', cmd)

    def show_info(self, title, code, out, err):
        typ = 'Success' if code == 0 else 'Error'
        txt = out.strip() or err.strip() or f'return code {code}'
        dlg = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=f'{title}: {typ}\n\n{txt}'
        )
        self._run_dialog_blocking(dlg)

    def clear_listbox(self, listbox: Gtk.ListBox):
        child = listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            listbox.remove(child)
            child = next_child

    def _apply_css(self):
        css = b'''
        window {
            background: #f5f5f5;
            color: #111;
        }
        headerbar {
            background: #ededed;
            color: #111;
        }
        scrolledwindow {
            background: #ffffff;
        }
        listbox row {
            background: #ffffff;
            color: #111;
            padding: 4px;
        }
        button {
            background: #3b4252;
            color: #f4f6fb;
            border-radius: 6px;
            padding: 4px 10px;
        }
        button:hover {
            background: #4c566a;
        }
        button:active {
            background: #2e3440;
        }
        label {
            color: #111;
        }
        '''
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _set_dialog_secondary(self, dialog: Gtk.MessageDialog, text: str):
        # Deprecated helper kept for compatibility; not used after inlined text approach.
        dialog.set_property('text', f"{dialog.get_property('text')}\n\n{text}")

    def _run_dialog_blocking(self, dialog: Gtk.MessageDialog):
        response_holder = {'resp': None}

        def on_response(dlg, resp):
            response_holder['resp'] = resp
            dlg.hide()
            loop.quit()

        loop = GLib.MainLoop()
        dialog.connect('response', on_response)
        dialog.present()
        loop.run()
        dialog.destroy()
        return response_holder['resp']

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

        lbl = Gtk.Label(label=f'Running: {cmd}')
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

        btn_close = Gtk.Button(label='Close')
        btn_close.set_sensitive(False)
        btn_close.connect('clicked', lambda b: dialog.destroy())
        vbox.append(btn_close)

        dialog.show()

        def append_text(text):
            GLib.idle_add(lambda: output_buf.insert(output_buf.get_end_iter(), text))

        def worker():
            full_cmd = cmd
            if shutil_which('pkexec'):
                full_cmd = f'pkexec bash -c {shlex.quote(cmd)}'
            proc = subprocess.Popen(full_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                append_text(line)
            proc.wait()
            rc = proc.returncode
            GLib.idle_add(self._finish_long_command, dialog, spinner, btn_close, rc)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_long_command(self, dialog, spinner, btn_close, rc):
        spinner.set_spinning(False)
        btn_close.set_sensitive(True)
        dialog.set_title(f'{dialog.get_title()} — done (rc={rc})')
        return False


def shutil_which(cmd):
    from shutil import which
    return which(cmd) is not None
