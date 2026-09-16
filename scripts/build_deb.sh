#!/usr/bin/env bash
set -euo pipefail

# Build script for Debian package (.deb)
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$PROJECT_DIR/dist"

mkdir -p "$DIST_DIR"
cd "$PROJECT_DIR"

echo "==> Building Debian package..."
dpkg-buildpackage -us -uc -b

PKG_VERSION=$(grep '^version' "$PROJECT_DIR/pyproject.toml" | sed 's/version = "\(.*\)"/\1/')
DEB_NAME="linecast_${PKG_VERSION}-1_all.deb"

if [ -f "$PROJECT_DIR/../$DEB_NAME" ]; then
  mv "$PROJECT_DIR/../linecast_${PKG_VERSION}"*.* "$DIST_DIR/"
fi

echo "==> Verifying Debian package with lintian..."
if command -v lintian >/dev/null 2>&1; then
  lintian "$DIST_DIR/$DEB_NAME" || true
fi

echo "==> Package ready at:"
ls -lh "$DIST_DIR/$DEB_NAME"
