#!/usr/bin/env python3
"""
Build SASS files to CSS for Greg AI Playground
"""
import subprocess
import sys
import os
from pathlib import Path
import argparse
import time

def check_sass_installed():
    """Check if sass is installed"""
    try:
        result = subprocess.run(['sass', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_sass():
    """Install sass via npm"""
    print("📦 Installing Dart Sass...")
    
    # Check if npm is available
    try:
        subprocess.run(['npm', '--version'], check=True, capture_output=True)
    except FileNotFoundError:
        print("❌ npm not found. Please install Node.js first.")
        print("   Visit: https://nodejs.org/")
        return False
    
    # Install sass globally
    try:
        subprocess.run(['npm', 'install', '-g', 'sass'], check=True)
        print("✅ Sass installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install sass. Try running: sudo npm install -g sass")
        return False

def build_sass(watch=False, compressed=False):
    """Build SASS files to CSS"""
    project_root = Path(__file__).parent.parent
    scss_dir = project_root / "static" / "scss"
    css_dir = project_root / "static" / "css"
    
    # Create CSS directory if it doesn't exist
    css_dir.mkdir(parents=True, exist_ok=True)
    
    # Build command
    cmd = ['sass']
    
    if watch:
        cmd.append('--watch')
    
    if compressed:
        cmd.extend(['--style', 'compressed'])
    else:
        cmd.extend(['--style', 'expanded'])
    
    # Add source map
    cmd.append('--source-map')
    
    # Input and output
    cmd.append(f"{scss_dir}/main.scss:{css_dir}/main.css")
    
    print(f"🎨 Building SASS files...")
    print(f"   Source: {scss_dir}/main.scss")
    print(f"   Output: {css_dir}/main.css")
    
    if watch:
        print(f"👀 Watching for changes...")
        print(f"   Press Ctrl+C to stop")
    
    try:
        # Run sass compiler
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Stream output
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"   {line.strip()}")
        
        process.wait()
        
        if process.returncode == 0 and not watch:
            print("✅ Build complete!")
            
            # Show file sizes
            css_file = css_dir / "main.css"
            if css_file.exists():
                size = css_file.stat().st_size / 1024
                print(f"   Size: {size:.1f} KB")
        
    except KeyboardInterrupt:
        print("\n⏹️  Build stopped.")
        process.terminate()
    except Exception as e:
        print(f"❌ Build failed: {e}")
        return False
    
    return True

def clean_css():
    """Remove compiled CSS files"""
    project_root = Path(__file__).parent.parent
    css_dir = project_root / "static" / "css"
    
    if css_dir.exists():
        for css_file in css_dir.glob("*.css*"):
            css_file.unlink()
            print(f"🗑️  Removed: {css_file.name}")
    
    print("✅ Clean complete!")

def main():
    parser = argparse.ArgumentParser(description='Build SASS files for Greg AI Playground')
    parser.add_argument('--watch', '-w', action='store_true', help='Watch for changes')
    parser.add_argument('--compressed', '-c', action='store_true', help='Compress output')
    parser.add_argument('--clean', action='store_true', help='Remove compiled CSS files')
    parser.add_argument('--install', action='store_true', help='Install sass if not available')
    
    args = parser.parse_args()
    
    if args.clean:
        clean_css()
        return
    
    # Check if sass is installed
    if not check_sass_installed():
        print("⚠️  Sass is not installed.")
        
        if args.install or input("Install sass now? (y/n): ").lower() == 'y':
            if not install_sass():
                sys.exit(1)
        else:
            print("❌ Cannot build without sass. Install with: npm install -g sass")
            sys.exit(1)
    
    # Build SASS
    success = build_sass(watch=args.watch, compressed=args.compressed)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()