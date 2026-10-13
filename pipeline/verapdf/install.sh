#!/usr/bin/env bash
# Install the veraPDF command-line validator (greenfield build, no GUI) without prompts.
#   bash verapdf/install.sh [INSTALL_DIR]        default: ~/.local/opt/verapdf
# Needs Java 11+ (17 recommended) on PATH, curl and python3. Prints the path to set as VERAPDF.
set -euo pipefail
DEST=${1:-$HOME/.local/opt/verapdf}
VERSION=${VERAPDF_VERSION:-1.30.3}
command -v java > /dev/null || { echo "java not found: install a Java 17 runtime first"; exit 1; }
DEST=$(mkdir -p "$DEST" && cd "$DEST" && pwd)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
curl -fsSL -o "$TMP/installer.zip" "https://software.verapdf.org/rel/${VERSION%.*}/verapdf-greenfield-$VERSION-installer.zip" \
  || curl -fsSL -o "$TMP/installer.zip" https://software.verapdf.org/releases/verapdf-installer.zip
python3 -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$TMP/installer.zip" "$TMP/x"
JAR=$(find "$TMP/x" -name 'verapdf-izpack-installer-*.jar' | head -1)
[[ -n $JAR ]] || { echo "installer jar not found in the download"; exit 1; }
cat > "$TMP/auto-install.xml" <<XML
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<AutomatedInstallation langpack="eng">
  <com.izforge.izpack.panels.htmlhello.HTMLHelloPanel id="welcome"/>
  <com.izforge.izpack.panels.target.TargetPanel id="install_dir"><installpath>$DEST</installpath></com.izforge.izpack.panels.target.TargetPanel>
  <com.izforge.izpack.panels.packs.PacksPanel id="sdk_pack_select">
    <pack index="0" name="veraPDF GUI" selected="false"/>
    <pack index="1" name="veraPDF Mac and *nix Scripts" selected="true"/>
    <pack index="2" name="veraPDF Validation model" selected="true"/>
    <pack index="3" name="veraPDF Documentation" selected="false"/>
    <pack index="4" name="veraPDF Sample Plugins" selected="false"/>
  </com.izforge.izpack.panels.packs.PacksPanel>
  <com.izforge.izpack.panels.install.InstallPanel id="install"/>
  <com.izforge.izpack.panels.finish.FinishPanel id="finish"/>
</AutomatedInstallation>
XML
java -jar "$JAR" "$TMP/auto-install.xml" > "$TMP/install.log" 2>&1 || { cat "$TMP/install.log"; exit 1; }
[[ -x $DEST/verapdf ]] || { cat "$TMP/install.log"; echo "install finished but $DEST/verapdf is missing"; exit 1; }
"$DEST/verapdf" --version | head -1
echo "export VERAPDF=$DEST/verapdf"
