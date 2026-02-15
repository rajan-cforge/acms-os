# ACMS Desktop Icons

## Current Status: Placeholder Icons

The desktop app currently uses placeholder text-based icons. For production:

1. Convert `icon.svg` to PNG files:
   - icon.png (512x512) - Main app icon
   - tray-icon.png (22x22 for macOS, 16x16 for Windows) - System tray icon

## Converting SVG to PNG

### Using macOS (sips + qlmanage):
```bash
# Generate PNG from SVG
qlmanage -t -s 512 -o . icon.svg
mv icon.svg.png icon.png

# Create tray icon
sips -z 22 22 icon.png --out tray-icon.png
```

### Using ImageMagick (if installed):
```bash
# Main icon
convert icon.svg -resize 512x512 icon.png

# Tray icon (macOS)
convert icon.svg -resize 22x22 tray-icon.png

# Multiple sizes for Windows
convert icon.svg -resize 16x16 icon-16.png
convert icon.svg -resize 48x48 icon-48.png
convert icon.svg -resize 128x128 icon-128.png
```

### Using Node.js (sharp package):
```bash
npm install sharp
node convert-icons.js
```

## Icon Specifications

### App Icon:
- macOS: 512x512 (Retina), 256x256, 128x128, 64x64, 32x32, 16x16
- Windows: 256x256, 128x128, 96x96, 64x64, 48x48, 32x32, 16x16
- Linux: 512x512, 256x256, 128x128, 64x64, 32x32, 16x16

### Tray Icon:
- macOS: 22x22 (16px with 3px padding), 44x44 for Retina
- Windows: 16x16, 32x32 for high DPI
- Linux: 22x22, 44x44

## Current Workaround

The app uses emoji/text-based placeholder icons in the UI:
- ✅ Works immediately without conversion
- ❌ Not ideal for production
- Replace with proper PNG icons before release
