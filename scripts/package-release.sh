#!/usr/bin/env bash
set -euo pipefail

version="${1:-}"
if [[ ! "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Usage: $0 vMAJOR.MINOR.PATCH" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
distribution_dir="$repo_root/dist"
archive_name="codex-split-editor-${version}.tar.gz"
staging_dir="$(mktemp -d)"
trap 'rm -rf "$staging_dir"' EXIT

package_root="$staging_dir/codex-split-editor-${version}"
mkdir -p "$package_root"
install -m 0755 "$repo_root/codex-split" "$package_root/codex-split"
install -m 0755 "$repo_root/codex-split-editor" "$package_root/codex-split-editor"
install -m 0644 "$repo_root/README.md" "$package_root/README.md"
install -m 0644 "$repo_root/README.ja.md" "$package_root/README.ja.md"
install -m 0644 "$repo_root/LICENSE" "$package_root/LICENSE"
install -m 0644 "$repo_root/plugin.json" "$package_root/plugin.json"
install -m 0644 "$repo_root/package.json" "$package_root/package.json"
mkdir -p "$package_root/scripts" "$package_root/.agents/plugins" "$package_root/skills/manage-codex-split-editor"
install -m 0755 "$repo_root/scripts/setup.py" "$package_root/scripts/setup.py"
install -m 0644 "$repo_root/.agents/plugins/marketplace.json" "$package_root/.agents/plugins/marketplace.json"
install -m 0644 "$repo_root/skills/manage-codex-split-editor/SKILL.md" "$package_root/skills/manage-codex-split-editor/SKILL.md"

mkdir -p "$distribution_dir"
python3 - "$package_root" "$distribution_dir/$archive_name" <<'PY'
import gzip
import os
import sys
import tarfile

package_root, archive_path = sys.argv[1:]
archive_name = os.path.basename(package_root)
with open(archive_path, "wb") as raw:
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            paths = []
            for directory, subdirectories, filenames in os.walk(package_root):
                subdirectories.sort()
                filenames.sort()
                for filename in filenames:
                    paths.append(os.path.join(directory, filename))
            for path in sorted(paths):
                relative = os.path.relpath(path, package_root)
                info = archive.gettarinfo(path, arcname=f"{archive_name}/{relative}")
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 1577836800
                with open(path, "rb") as content:
                    archive.addfile(info, content)
PY
python3 - "$distribution_dir/$archive_name" "$distribution_dir/$archive_name.sha256" <<'PY'
import hashlib
import sys

archive_path, checksum_path = sys.argv[1:]
digest = hashlib.sha256(open(archive_path, "rb").read()).hexdigest()
with open(checksum_path, "w", encoding="ascii") as output:
    output.write(f"{digest}  {archive_path.split('/')[-1]}\n")
PY
printf 'Created %s and checksum\n' "$distribution_dir/$archive_name"
