#!/usr/bin/env bash
set -euo pipefail

PKG=snapmanager-proto
VER=0.1
WORKDIR=$(pwd)/packaging/deb/build
mkdir -p "$WORKDIR/DEBIAN"
mkdir -p "$WORKDIR/usr/bin"
cp -r ../../* "$WORKDIR/usr/bin/"
cat > "$WORKDIR/DEBIAN/control" <<EOF
Package: $PKG
Version: $VER
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-gi
Maintainer: SnapManager Prototype <noreply@example.com>
Description: Prototype GTK4 Snap manager
EOF

dpkg-deb --build "$WORKDIR" ../${PKG}_${VER}.deb
echo "Built ../${PKG}_${VER}.deb"
