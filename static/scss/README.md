# Greg AI Playground - SASS Styling Guide

This directory contains all the SASS files for styling the Greg AI Playground Streamlit app.

## Structure

```
scss/
├── main.scss              # Main entry point - imports all other files
├── base/                  # Base styles
│   ├── _reset.scss       # CSS reset and normalization
│   ├── _typography.scss  # Typography rules
│   └── _animations.scss  # Keyframe animations
├── utils/                 # Utilities and helpers
│   ├── _variables.scss   # Design tokens (colors, spacing, etc.)
│   ├── _mixins.scss      # Reusable mixins
│   └── _functions.scss   # SASS functions
├── layout/               # Layout components
│   ├── _grid.scss        # Grid system
│   ├── _header.scss      # Header styles
│   ├── _sidebar.scss     # Sidebar styles
│   └── _main.scss        # Main content area
├── components/           # UI components
│   ├── _buttons.scss     # Button styles
│   ├── _chat-interface.scss  # Chat UI
│   ├── _drag-drop.scss   # Drag & drop upload
│   ├── _toast.scss       # Toast notifications
│   └── ...               # Other components
├── pages/                # Page-specific styles
│   └── _app.scss         # Main app page
└── vendor/               # Third-party overrides
    └── _streamlit-overrides.scss  # Streamlit-specific CSS
```

## Building CSS

### Development
```bash
# Build once
make sass

# Watch for changes
make sass-watch
```

### Production
```bash
# Build minified CSS
make sass-compressed
```

### Manual build
```bash
# If make isn't available
python scripts/build_sass.py --compressed
```

## Design System

### Colors
Primary colors are defined in `utils/_variables.scss`:
- Primary: `$primary-color` (#4A90E2)
- Secondary: `$secondary-color` (#667eea)
- Success: `$success-color` (#10b981)
- Error: `$error-color` (#ef4444)

### Spacing
Using a consistent spacing scale:
- xs: 0.25rem (4px)
- sm: 0.5rem (8px)
- md: 1rem (16px)
- lg: 1.5rem (24px)
- xl: 2rem (32px)

### Typography
- Base font: System font stack
- Monospace: SF Mono, Monaco, Consolas
- Font sizes: xs through 4xl
- Line heights: tight, normal, relaxed

## Adding New Styles

1. Create a new partial file in the appropriate directory (prefix with `_`)
2. Import it in `main.scss` in the correct section
3. Use existing variables and mixins where possible
4. Run `make sass` to build

## Component Example

```scss
// components/_my-component.scss
.my-component {
  padding: $spacing-md;
  background: $bg-secondary;
  border-radius: $radius-md;
  
  @include breakpoint('md') {
    padding: $spacing-lg;
  }
  
  &__title {
    font-size: $font-size-lg;
    color: $text-primary;
    margin-bottom: $spacing-sm;
  }
  
  &--variant {
    background: $primary-light;
  }
}
```

## Streamlit-Specific Styling

Streamlit uses specific data-testid attributes for components. Common selectors:
- `[data-testid="stSidebar"]` - Sidebar container
- `[data-testid="stButton"]` - Buttons
- `[data-testid="stSelectbox"]` - Select dropdowns
- `[data-testid="stFileUploader"]` - File upload
- `[data-testid="stChatMessage"]` - Chat messages

## Best Practices

1. **Use Variables**: Always use variables for colors, spacing, etc.
2. **Mobile First**: Use min-width breakpoints
3. **BEM Naming**: Use Block__Element--Modifier convention
4. **Nesting**: Don't nest more than 3 levels deep
5. **Mixins**: Create mixins for repeated patterns
6. **Comments**: Document complex styles

## Troubleshooting

### CSS not updating
1. Clear browser cache
2. Hard refresh (Cmd+Shift+R or Ctrl+Shift+R)
3. Check if SASS build succeeded
4. Verify CSS file exists in `static/css/`

### Build errors
1. Check for syntax errors in SCSS files
2. Ensure all imported files exist
3. Check variable references are defined
4. Run `npm install -g sass` if sass command not found

### Streamlit not loading styles
1. Ensure `load_app_styles()` is called in app.py
2. Check browser console for errors
3. Verify CSS file path is correct
4. Try force reload with `load_app_styles(force_reload=True)`