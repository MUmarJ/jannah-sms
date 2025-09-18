#!/usr/bin/env python3
"""
Theme Switcher for SMS Admin Application

This utility helps you quickly switch between different app themes
by copying the appropriate .env configuration file.
"""

import os
import shutil
import sys
from pathlib import Path

def list_themes():
    """List available theme configurations."""
    theme_files = list(Path('.').glob('.env.*'))
    themes = {}

    for file in theme_files:
        if file.name == '.env.example':
            themes['example'] = {
                'file': file,
                'name': 'Jannah SMS Admin (Default)',
                'description': 'Original Jannah SMS theme'
            }
        elif file.name == '.env.goodtenant':
            themes['goodtenant'] = {
                'file': file,
                'name': 'GoodTenant',
                'description': 'Green-themed property management platform'
            }

    return themes

def apply_theme(theme_key):
    """Apply a theme by copying the appropriate .env file."""
    themes = list_themes()

    if theme_key not in themes:
        print(f"❌ Theme '{theme_key}' not found!")
        print("Available themes:")
        for key, theme in themes.items():
            print(f"  • {key}: {theme['name']} - {theme['description']}")
        return False

    theme = themes[theme_key]

    # Backup existing .env if it exists
    if os.path.exists('.env'):
        backup_name = f'.env.backup.{int(os.path.getmtime(".env"))}'
        print(f"📁 Backing up existing .env to {backup_name}")
        shutil.copy2('.env', backup_name)

    # Copy theme file to .env
    print(f"🎨 Applying theme: {theme['name']}")
    shutil.copy2(theme['file'], '.env')

    print(f"✅ Theme applied successfully!")
    print(f"🚀 Restart the application to see changes")

    return True

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("🎨 Theme Switcher for SMS Admin Application")
        print("\nUsage:")
        print("  python theme_switcher.py <theme_name>")
        print("  python theme_switcher.py list")
        print("\nAvailable themes:")

        themes = list_themes()
        for key, theme in themes.items():
            print(f"  • {key}: {theme['name']} - {theme['description']}")

        return

    command = sys.argv[1].lower()

    if command == 'list':
        print("Available themes:")
        themes = list_themes()
        for key, theme in themes.items():
            print(f"  • {key}: {theme['name']} - {theme['description']}")
    else:
        apply_theme(command)

if __name__ == "__main__":
    main()