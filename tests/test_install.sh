#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_dir="$(mktemp -d)"
trap 'rm -rf -- "$test_dir"' EXIT

project="$test_dir/project"
mkdir -p "$project/.agents/skills/unrelated"
printf 'keep\n' > "$project/.agents/skills/unrelated/marker"

bash "$root/install.sh" --codex --yes "$project"
for source in "$root"/skills/*/SKILL.md; do
    name="$(basename "$(dirname "$source")")"
    destination="$project/.agents/skills/$name"
    test -L "$destination"
    test "$(readlink "$destination")" = "$root/skills/$name"
done
test -f "$project/.agents/skills/unrelated/marker"

bash "$root/install.sh" --codex --copy --force --yes "$project"
for source in "$root"/skills/*/SKILL.md; do
    name="$(basename "$(dirname "$source")")"
    destination="$project/.agents/skills/$name"
    test -d "$destination"
    test ! -L "$destination"
    cmp "$source" "$destination/SKILL.md"
done
test -f "$project/.agents/skills/unrelated/marker"

dcode_project="$test_dir/dcode-project"
mkdir -p "$dcode_project"
bash "$root/install.sh" --dcode --yes "$dcode_project"
for source in "$root"/skills/*/SKILL.md; do
    name="$(basename "$(dirname "$source")")"
    test -L "$dcode_project/.deepagents/skills/$name"
done

echo "Installer link and copy checks passed."
