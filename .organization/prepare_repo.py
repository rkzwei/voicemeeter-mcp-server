"""Prepare the Voicemeeter MCP Server repository for GitHub and marketplace submission."""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[OK] {description} completed successfully")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"[ERROR] {description} failed")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"[ERROR] {description} failed with exception: {e}")
        return False

def check_git_status():
    """Check if we're in a git repository and show status."""
    print("=" * 60)
    print("GIT REPOSITORY STATUS")
    print("=" * 60)
    
    if not os.path.exists('.git'):
        print("[ERROR] Not a git repository")
        print("   Run 'git init' to initialize a repository")
        return False
    
    print("[OK] Git repository detected")
    
    # Check git status
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if result.returncode == 0:
        if result.stdout.strip():
            print("📝 Uncommitted changes detected:")
            for line in result.stdout.strip().split('\n'):
                print(f"   {line}")
        else:
            print("[OK] Working directory clean")
    
    # Check remote
    result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        print("🔗 Remote repositories:")
        for line in result.stdout.strip().split('\n'):
            print(f"   {line}")
    else:
        print("[WARNING]️  No remote repository configured")
        print("   Add remote with: git remote add origin https://github.com/USERNAME/voicemeeter-mcp-server.git")
    
    return True

def validate_files():
    """Validate that all required files are present."""
    print("\n" + "=" * 60)
    print("FILE VALIDATION")
    print("=" * 60)
    
    required_files = [
        'README.md',
        'llms-install.md',
        'LICENSE',
        'logo.png',
        'pyproject.toml',
        'src/voicemeeter_mcp_server/__init__.py',
        'src/voicemeeter_mcp_server/main.py',
        'src/voicemeeter_mcp_server/server.py',
        'src/voicemeeter_mcp_server/voicemeeter_api.py',
        'tests/test_voicemeeter_api.py',
        'troubleshoot.py',
        'install.py',
        'MARKETPLACE_SUBMISSION.md'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"[OK] {file_path} ({size:,} bytes)")
        else:
            print(f"[ERROR] {file_path} - MISSING")
            missing_files.append(file_path)
    
    # Check optional directories
    optional_dirs = ['audio_samples', 'presets']
    for dir_path in optional_dirs:
        if os.path.exists(dir_path):
            files = list(Path(dir_path).rglob('*'))
            file_count = len([f for f in files if f.is_file()])
            print(f"[OK] {dir_path}/ ({file_count} files)")
        else:
            print(f"[WARNING]️  {dir_path}/ - Optional directory missing")
    
    if missing_files:
        print(f"\n[ERROR] {len(missing_files)} required files missing!")
        return False
    else:
        print(f"\n[OK] All {len(required_files)} required files present")
        return True

def check_logo():
    """Validate the logo file."""
    print("\n" + "=" * 60)
    print("LOGO VALIDATION")
    print("=" * 60)
    
    if not os.path.exists('logo.png'):
        print("[ERROR] logo.png not found")
        print("   Run 'python create_logo.py' to generate the logo")
        return False
    
    try:
        from PIL import Image
        with Image.open('logo.png') as img:
            width, height = img.size
            format_type = img.format
            
            print(f"[OK] Logo file found")
            print(f"   Size: {width}x{height} pixels")
            print(f"   Format: {format_type}")
            print(f"   File size: {os.path.getsize('logo.png'):,} bytes")
            
            if width == 400 and height == 400:
                print("[OK] Logo dimensions correct (400x400)")
            else:
                print("[ERROR] Logo dimensions incorrect (should be 400x400)")
                return False
                
            if format_type == 'PNG':
                print("[OK] Logo format correct (PNG)")
            else:
                print("[ERROR] Logo format incorrect (should be PNG)")
                return False
                
            return True
            
    except ImportError:
        print("[WARNING]️  Cannot validate logo - Pillow not installed")
        print("   Install with: pip install Pillow")
        return True  # Don't fail if Pillow not available
    except Exception as e:
        print(f"[ERROR] Error validating logo: {e}")
        return False

def run_tests():
    """Run the test suite to ensure everything works."""
    print("\n" + "=" * 60)
    print("RUNNING TESTS")
    print("=" * 60)
    
    tests = [
        ('python install.py', 'Installation check'),
        ('python test_mcp_simple.py', 'Simple MCP test'),
        ('python troubleshoot.py', 'Troubleshooting script')
    ]
    
    all_passed = True
    
    for cmd, description in tests:
        success = run_command(cmd, description)
        if not success:
            all_passed = False
    
    return all_passed

def create_gitignore():
    """Create or update .gitignore file."""
    print("\n" + "=" * 60)
    print("GITIGNORE SETUP")
    print("=" * 60)
    
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
samples/
*.log
.pytest_cache/
.coverage
htmlcov/

# Audio samples (optional - can be regenerated)
# audio_samples/*.wav

# Temporary files
*.tmp
*.temp
"""
    
    try:
        with open('.gitignore', 'w') as f:
            f.write(gitignore_content)
        print("[OK] .gitignore created/updated")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create .gitignore: {e}")
        return False

def show_next_steps():
    """Show the next steps for repository setup and submission."""
    print("\n" + "=" * 60)
    print("NEXT STEPS FOR REPOSITORY SETUP")
    print("=" * 60)
    
    print("1. 📁 Create GitHub Repository:")
    print("   - Go to https://github.com/new")
    print("   - Repository name: voicemeeter-mcp-server")
    print("   - Description: MCP Server for Voicemeeter Remote API - Control audio mixing and routing through AI agents")
    print("   - Make it Public")
    print("   - Don't initialize with README (we have our own)")
    
    print("\n2. 🔗 Connect Local Repository to GitHub:")
    print("   git remote add origin https://github.com/YOUR_USERNAME/voicemeeter-mcp-server.git")
    print("   git branch -M main")
    print("   git push -u origin main")
    
    print("\n3. 📝 Commit and Push:")
    print("   git add .")
    print("   git commit -m \"Initial release: Voicemeeter MCP Server v1.0.0\"")
    print("   git push")
    
    print("\n4. 🏪 Submit to MCP Marketplace:")
    print("   - Go to: https://github.com/cline/mcp-marketplace/issues/new?template=mcp-server-submission.yml")
    print("   - GitHub Repo URL: https://github.com/YOUR_USERNAME/voicemeeter-mcp-server")
    print("   - Upload logo.png (400x400 PNG)")
    print("   - Copy reason from MARKETPLACE_SUBMISSION.md")
    
    print("\n5. 📋 Repository Settings (Optional):")
    print("   - Add topics: mcp, voicemeeter, audio, ai-agent, python")
    print("   - Enable Issues and Discussions")
    print("   - Add repository description")
    print("   - Set up GitHub Pages for documentation (optional)")

def main():
    """Main function to prepare the repository."""
    print("VOICEMEETER MCP SERVER - REPOSITORY PREPARATION")
    print("=" * 60)
    print("This script prepares the repository for GitHub and marketplace submission")
    print()
    
    # Change to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    all_checks_passed = True
    
    # Run all checks
    checks = [
        check_git_status,
        validate_files,
        check_logo,
        create_gitignore,
        run_tests
    ]
    
    for check in checks:
        try:
            if not check():
                all_checks_passed = False
        except Exception as e:
            print(f"[ERROR] Check failed with exception: {e}")
            all_checks_passed = False
    
    # Show results
    print("\n" + "=" * 60)
    print("PREPARATION SUMMARY")
    print("=" * 60)
    
    if all_checks_passed:
        print("🎉 ALL CHECKS PASSED!")
        print("   Repository is ready for GitHub and marketplace submission")
        show_next_steps()
    else:
        print("[ERROR] SOME CHECKS FAILED")
        print("   Please fix the issues above before proceeding")
        print("   Run this script again after making corrections")
    
    return all_checks_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
