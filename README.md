# SnapManager (prototype)

GTK-4 Prototype for managing updates and issues on snaps.
<img width="928" height="629" alt="image" src="https://github.com/user-attachments/assets/01b0dee8-f69c-4ed3-a2fa-e2e84a1c3f1f" />

### Work in progress.

### Highlights
- Snap & apt lists with friendly error messages and guided actions.
- Snap Problem Solver that interprets diagnostics and recommends fixes.
- A small snap→apt database (`snapmanager/data/snap_to_apt.json`) that the UI consults before suggesting apt replacements, so it can point to the right deb or tell you when only a snap build exists.
