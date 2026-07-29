#!/usr/bin/env python3
"""
Universal Python File Flattener

Moves ALL .py files from your home directory into a single folder.
Safely handles naming conflicts, preserves backups, and updates imports.

Usage:
    python3 flatten_all_py.py

By default creates: ~/All_Python_Files/
"""

import os
import re
import shutil
import sys
from pathlib import Path
from datetime import datetime

# ─── Configuration ──────────────────────────────────────────────────────────

HOME = Path.home()
TARGET_FOLDER = HOME / "All_Python_Files"
BACKUP_FOLDER = HOME / f"All_Python_Files_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
DRY_RUN = False  # Set True to preview without moving anything

# Folders to EXCLUDE (never scan these)
EXCLUDED_ROOTS = {
    str(HOME / ".local"),          # pipx, pip, etc
    str(HOME / ".config"),
    str(HOME / ".cache"),
    str(HOME / ".Trash"),
    str(HOME / "Library"),         # macOS system
    str(HOME / "Applications"),
    str(TARGET_FOLDER),             # don't scan the target itself
    str(BACKUP_FOLDER),
}

# ─── Core Functions ─────────────────────────────────────────────────────────

def should_exclude(path):
    """Check if path is in an excluded root or hidden directory."""
    path_str = str(path.resolve())

    # Exclude hidden directories anywhere in the path
    for part in path.parts:
        if part.startswith('.') and part not in ('.', '..'):
            return True

    # Exclude system roots
    for excluded in EXCLUDED_ROOTS:
        if path_str.startswith(excluded):
            return True

    return False


def find_all_py_files():
    """Find every .py file under HOME that isn't excluded."""
    py_files = []

    for entry in os.scandir(HOME):
        if not entry.is_dir():
            continue
        if should_exclude(Path(entry.path)):
            continue

        # Walk this directory tree
        for root, dirs, files in os.walk(entry.path):
            # Skip hidden subdirectories during walk
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                if file.endswith('.py'):
                    full_path = Path(root) / file
                    if not should_exclude(full_path.parent):
                        py_files.append(full_path)

    # Also check loose .py files directly in HOME
    for entry in os.scandir(HOME):
        if entry.is_file() and entry.name.endswith('.py'):
            py_files.append(Path(entry.path))

    return sorted(set(py_files))


def handle_naming_conflict(target_folder, filename, source_path):
    """Create unique filename if collision occurs."""
    dest = target_folder / filename

    if not dest.exists():
        return dest

    # Strategy: prefix with parent folder name
    parent_name = source_path.parent.name
    new_name = f"{parent_name}_{filename}"
    dest = target_folder / new_name

    if not dest.exists():
        return dest

    # Final fallback: numbered suffix
    stem = Path(new_name).stem
    suffix = Path(new_name).suffix
    counter = 1
    while True:
        final_name = f"{stem}_{counter:03d}{suffix}"
        dest = target_folder / final_name
        if not dest.exists():
            return dest
        counter += 1


def update_imports(content, all_filenames):
    """Update imports to work in flat structure."""
    modified = content
    changes = []

    # Pattern: from package.module import X
    for match in re.finditer(r'^from\s+([\w.]+)\s+import', content, re.MULTILINE):
        old_path = match.group(1)
        module_name = old_path.split('.')[-1]

        if f"{module_name}.py" in all_filenames:
            old_pattern = rf'from\s+{re.escape(old_path)}\s+import'
            new_pattern = f'from {module_name} import'
            modified = re.sub(old_pattern, new_pattern, modified, count=1)
            changes.append(f"from {old_path} → from {module_name}")

    # Pattern: import package.module
    for match in re.finditer(r'^import\s+([\w.]+)', content, re.MULTILINE):
        old_path = match.group(1)
        module_name = old_path.split('.')[-1]

        if f"{module_name}.py" in all_filenames:
            old_pattern = rf'^import\s+{re.escape(old_path)}\b'
            new_pattern = f'import {module_name}'
            modified = re.sub(old_pattern, new_pattern, modified, count=1, flags=re.MULTILINE)
            changes.append(f"import {old_path} → import {module_name}")

    return modified, changes


def main():
    print(f"{'='*60}")
    print(f"Universal Python File Flattener")
    print(f"{'='*60}")
    print(f"Home: {HOME}")
    print(f"Target: {TARGET_FOLDER}")
    print(f"Mode: {'DRY RUN (preview only)' if DRY_RUN else 'LIVE'}")
    print(f"{'='*60}\n")

    # Find all Python files
    print("Scanning for .py files...")
    all_py_files = find_all_py_files()

    print(f"Found {len(all_py_files)} Python files:\n")

    # Show first 20 and summary
    for i, f in enumerate(all_py_files[:20]):
        rel = f.relative_to(HOME)
        print(f"  {i+1}. {rel}")

    if len(all_py_files) > 20:
        print(f"  ... and {len(all_py_files) - 20} more files")

    if len(all_py_files) == 0:
        print("\nNo Python files found outside excluded directories.")
        return

    # Confirm
    if not DRY_RUN:
        print(f"\n{'─'*60}")
        response = input(f"Move ALL {len(all_py_files)} files to {TARGET_FOLDER.name}/? [yes/no]: ")
        if response.lower() not in ('yes', 'y'):
            print("Aborted.")
            return

    # Create folders
    if not DRY_RUN:
        TARGET_FOLDER.mkdir(exist_ok=True)
        BACKUP_FOLDER.mkdir(exist_ok=True)
        print(f"\n✓ Created: {TARGET_FOLDER}")
        print(f"✓ Backup: {BACKUP_FOLDER}")
    else:
        print(f"\n[DRY] Would create: {TARGET_FOLDER}")
        print(f"[DRY] Would create: {BACKUP_FOLDER}")

    # Build filename registry for conflict detection
    all_filenames = [f.name for f in all_py_files]

    # Process files
    print(f"\n{'─'*60}")
    print("Moving files...")

    moved = 0
    skipped = 0
    import_fixes = 0

    for src in all_py_files:
        rel = src.relative_to(HOME)

        # Determine destination (handle conflicts)
        dest = handle_naming_conflict(TARGET_FOLDER, src.name, src)

        # Read content
        try:
            content = src.read_text(encoding='utf-8')
        except Exception as e:
            print(f"  ✗ Cannot read {rel}: {e}")
            skipped += 1
            continue

        # Update imports
        new_content, changes = update_imports(content, all_filenames)
        if changes:
            import_fixes += 1

        if DRY_RUN:
            print(f"  [DRY] {rel} → {TARGET_FOLDER.name}/{dest.name}")
            if changes:
                for c in changes[:3]:
                    print(f"        └─ {c}")
        else:
            # Backup original
            backup_dest = BACKUP_FOLDER / rel
            backup_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, backup_dest)

            # Write to destination
            dest.write_text(new_content, encoding='utf-8')

            # Remove original
            try:
                src.unlink()
            except Exception as e:
                print(f"  ⚠ Could not delete original {rel}: {e}")

            print(f"  ✓ {rel} → {dest.name}")

        moved += 1

    # Cleanup empty directories
    if not DRY_RUN:
        print(f"\n{'─'*60}")
        print("Cleaning up empty directories...")

        for entry in os.scandir(HOME):
            if not entry.is_dir():
                continue
            if should_exclude(Path(entry.path)):
                continue
            if entry.name == TARGET_FOLDER.name:
                continue

            removed = 0
            for root, dirs, files in os.walk(entry.path, topdown=False):
                for d in dirs:
                    dpath = Path(root) / d
                    try:
                        if dpath.exists() and not any(dpath.iterdir()):
                            dpath.rmdir()
                            removed += 1
                    except:
                        pass

            if removed > 0:
                print(f"  ✓ Removed {removed} empty dirs from {entry.name}/")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Files found:    {len(all_py_files)}")
    print(f"Files moved:    {moved}")
    print(f"Files skipped:  {skipped}")
    print(f"Imports fixed:  {import_fixes} files")
    print(f"\nAll files now in: {TARGET_FOLDER}")
    print(f"Backups saved to: {BACKUP_FOLDER}")

    if not DRY_RUN:
        print(f"\n⚠  IMPORTANT: Test your scripts before running them!")
        print(f"   Some imports may need manual fixing.")


if __name__ == "__main__":
    main()
