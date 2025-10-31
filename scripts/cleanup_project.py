"""
Clean up project by removing non-production files:
- Documentation files (keep only README.md)
- Test/debug scripts
- Temporary JSON files
- Old config files
"""
import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Files/directories to keep (production)
KEEP_FILES = {
    "README.md",
    "run.py",
    "Dockerfile",
    "fly.toml",
    "pyproject.toml",
    "uv.lock",
    "env.example",
    ".gitignore",
    ".cursor",
    ".github",
}

# Production scripts to keep
PRODUCTION_SCRIPTS = {
    "create_standalone_tools.py",
    "setup_new_assistant_complete.py",
    "deploy_to_fly.ps1",
    "start_dev.ps1",
    "sync_all_tools_to_vapi.py",  # Keep for maintenance
    "cleanup.ps1",  # Keep cleanup script
}

# Directories to keep
KEEP_DIRS = {
    "src",
    "tests",
    "scripts",  # Keep scripts dir but clean contents
    ".cursor",
    ".github",
    "__pycache__",  # Python cache (will be regenerated)
}


def should_delete_file(filepath: Path) -> bool:
    """Determine if a file should be deleted."""
    name = filepath.name
    
    # Keep production files
    if name in KEEP_FILES:
        return False
    
    # Delete all markdown except README.md
    if name.endswith(".md") and name != "README.md":
        return True
    
    # Delete temporary JSON files
    if name.endswith(".json"):
        if any(x in name for x in ["verify", "snapshot", "detail", "error", "debug", "call_detail", "new_call", "vapi_"]):
            return True
    
    # Delete local executables
    if name.endswith(".exe"):
        return True
    
    # Delete unused config files
    if name in ["render.yaml", "VAPI_DIAGNOSTIC_REPORT.txt"]:
        return True
    
    return False


def should_delete_script(script: Path) -> bool:
    """Determine if a script should be deleted."""
    name = script.name
    
    # Keep production scripts
    if name in PRODUCTION_SCRIPTS:
        return False
    
    # Delete test scripts
    if name.startswith("test_") or name.startswith("Test"):
        return True
    
    # Delete audit/check/verify scripts
    if any(name.startswith(prefix) for prefix in ["audit_", "check_", "verify_", "diagnose_", "get_", "monitor_", "wait_", "trigger_", "update_", "fix_", "deep_", "final_", "make_", "run_", "show_"]):
        return True
    
    # Keep deployment and setup scripts
    if name in ["deploy_to_fly.ps1", "start_dev.ps1", "cleanup.ps1"]:
        return False
    
    return False


def should_delete_dir(dirpath: Path) -> bool:
    """Determine if a directory should be deleted."""
    name = dirpath.name
    
    # Keep production directories
    if name in KEEP_DIRS:
        return False
    
    # Delete dashboard if it's just for testing
    if name == "dashboard":
        # Keep if it has production code, otherwise delete
        return True
    
    # Delete static test files
    if name == "static":
        return True
    
    # Delete docs (keep only .cursor/docs if needed)
    if name == "docs":
        return True
    
    return False


def cleanup_project():
    """Clean up the project."""
    deleted_files = []
    deleted_dirs = []
    
    print("=" * 80)
    print("🧹 PROJECT CLEANUP")
    print("=" * 80)
    print()
    
    # Clean root directory
    print("1️⃣ Cleaning root directory...")
    for item in PROJECT_ROOT.iterdir():
        if item.is_file():
            if should_delete_file(item):
                print(f"   🗑️  Deleting: {item.name}")
                item.unlink()
                deleted_files.append(item)
        elif item.is_dir() and item.name not in KEEP_DIRS:
            if should_delete_dir(item):
                print(f"   🗑️  Deleting directory: {item.name}/")
                shutil.rmtree(item)
                deleted_dirs.append(item)
            else:
                print(f"   ✓ Keeping: {item.name}/")
    
    # Clean scripts directory
    print()
    print("2️⃣ Cleaning scripts/ directory...")
    scripts_dir = PROJECT_ROOT / "scripts"
    if scripts_dir.exists():
        for script in scripts_dir.iterdir():
            if script.is_file() and should_delete_script(script):
                print(f"   🗑️  Deleting: {script.name}")
                script.unlink()
                deleted_files.append(script)
            elif script.is_file():
                print(f"   ✓ Keeping: {script.name}")
    
    # Clean __pycache__ directories
    print()
    print("3️⃣ Cleaning __pycache__ directories...")
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        print(f"   🗑️  Deleting: {pycache}")
        shutil.rmtree(pycache)
        deleted_dirs.append(pycache)
    
    print()
    print("=" * 80)
    print("✅ CLEANUP COMPLETE")
    print("=" * 80)
    print(f"   Files deleted: {len(deleted_files)}")
    print(f"   Directories deleted: {len(deleted_dirs)}")
    print()
    print("📋 Kept Production Files:")
    print("   - README.md")
    print("   - run.py, Dockerfile, fly.toml, pyproject.toml")
    print("   - src/ (all source code)")
    print("   - tests/ (test files)")
    print("   - Production scripts only")
    print()


if __name__ == "__main__":
    try:
        cleanup_project()
    except KeyboardInterrupt:
        print("\n⚠️  Cleanup cancelled by user")
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        raise
