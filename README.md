# SnapManager (prototype)

A minimal GTK4 prototype to help manage snaps and apt packages on Ubuntu.

Features (prototype):
- List installed snaps and apt packages.
- Hold/unhold snap auto-refresh globally or per snap (with optional 24h hold) using `snap refresh --hold/--unhold`.
- Show and run safe commands to hold/unhold apt packages.
- Show commands to switch an app to the apt version and to run snaps with relaxed confinement (requires user confirmation).

Important notes & limitations:
- This is a prototype built with Python and GTK4 (`PyGObject`).
- Some snap operations require elevated privileges; the app shows commands and can attempt to run them using `pkexec` or `sudo` if you confirm.
- Reinstalling snaps with `--devmode` or running unsandboxed may not be supported for store snaps and can be unsafe. Use with caution.

Dependencies (Ubuntu):
```sh
sudo apt update
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-4.0 snapd
python3 -m pip install --user pygments
```

Run locally:
```sh
python3 main.py
```

Packaging (examples):
- `snapcraft.yaml` is included for building a Snap.
- A simple `packaging/deb/make_deb.sh` script is included to build a `.deb` package.

Use this prototype as a starting point. It intentionally avoids performing destructive operations without an explicit, second confirmation.
