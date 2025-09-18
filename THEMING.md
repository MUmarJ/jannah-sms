# Dynamic Theming System

This application supports dynamic theming that allows you to rebrand it for different clients or use cases.

## How It Works

The theming system uses environment variables to control:
- Application name and branding
- Company information
- Visual styling (colors, icons)
- Meta information (taglines, versions)

## Available Theme Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `APP_NAME` | Application display name | `"GoodTenant"` |
| `COMPANY_NAME` | Company/organization name | `"GoodTenant Property Management"` |
| `APP_VERSION` | Version string | `"v2.0"` |
| `APP_TAGLINE` | Description for meta tags | `"Professional tenant communication platform"` |
| `APP_ICON` | Icon/emoji for branding | `"🏠"` |
| `PRIMARY_COLOR` | Primary brand color (hex) | `"#10b981"` |
| `SECONDARY_COLOR` | Secondary text color (hex) | `"#374151"` |

## Quick Theme Switching

Use the included theme switcher script to quickly switch between predefined themes:

```bash
# List available themes
python theme_switcher.py list

# Apply GoodTenant theme
python theme_switcher.py goodtenant

# Apply default Jannah SMS theme
python theme_switcher.py example
```

## Creating Custom Themes

1. Create a new `.env.yourtheme` file
2. Copy content from `.env.example`
3. Modify the theming variables
4. Add your theme to `theme_switcher.py` (optional)
5. Apply with: `python theme_switcher.py yourtheme`

## Example: GoodTenant Theme

```env
APP_NAME=GoodTenant
COMPANY_NAME=GoodTenant Property Management
APP_TAGLINE=Professional tenant communication platform
APP_ICON=🏠
PRIMARY_COLOR=#10b981
SECONDARY_COLOR=#374151
```

## Where Theming Is Applied

The theming system automatically updates:
- Page titles and meta descriptions
- Navigation branding
- Footer information
- CSS color variables
- Application icons

After changing theme variables, restart the application to see changes.