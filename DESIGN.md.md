---
version: alpha
name: Swasthya Cream and Brown Palette
description: "Swasthya visual system: warm cream backgrounds, off-white cards, and brown-only UI accents. Serif headings with Karla body text. Food photography may retain natural greens; interface chrome does not."
colors:
  primary: "#5B4636"
  on-primary: "#FAF7EE"
  primary-hover: "#463326"
  secondary: "#7A5C46"
  on-secondary: "#FAF7EE"
  muted: "#A68A72"
  background: "#FAF7EE"
  background-secondary: "#F3EBDD"
  on-background: "#463326"
  surface: "#FFFDF8"
  surface-alt: "#F3EBDD"
  on-surface: "#463326"
  on-surface-muted: "#7A5C46"
  outline: "#E5D8C6"
  success: "#5B4636"
  on-success: "#FAF7EE"
  error: "#7A4538"
  on-error: "#FAF7EE"
typography:
  display:
    fontFamily: Cormorant Garamond
    fontSize: 56px
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Cormorant Garamond
    fontSize: 40px
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Cormorant Garamond
    fontSize: 28px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Cormorant Garamond
    fontSize: 22px
    fontWeight: 600
    lineHeight: 1.25
  body-lg:
    fontFamily: Karla
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.7
  body-md:
    fontFamily: Karla
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
  body-sm:
    fontFamily: Karla
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
  label-lg:
    fontFamily: Karla
    fontSize: 16px
    fontWeight: 700
    lineHeight: 1.2
  label-md:
    fontFamily: Karla
    fontSize: 13px
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: 0.08em
  label-sm:
    fontFamily: Karla
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: 0.04em
  stat:
    fontFamily: Cormorant Garamond
    fontSize: 32px
    fontWeight: 600
    lineHeight: 1.0
    letterSpacing: -0.01em
rounded:
  none: 0px
  sm: 4px
  md: 6px
  lg: 10px
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  2xl: 64px
  3xl: 96px
  gutter: 24px
  max-width: 1200px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.md}"
    padding: 14px 24px
    height: 48px
  button-accent:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.md}"
    padding: 14px 24px
    height: 48px
  button-accent-hover:
    backgroundColor: "{colors.tertiary-hover}"
    textColor: "{colors.on-tertiary}"
  button-soft:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.on-soft}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.md}"
    padding: 14px 24px
  button-link:
    backgroundColor: "{colors.background}"
    textColor: "{colors.secondary}"
    typography: "{typography.label-lg}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: 12px 16px
    height: 48px
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: 24px
  card-alt:
    backgroundColor: "{colors.surface-alt}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: 24px
  card-featured:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.headline-md}"
    rounded: "{rounded.lg}"
    padding: 32px
  eyebrow:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.secondary}"
    typography: "{typography.label-md}"
  chip:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.on-soft}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.full}"
    padding: 4px 12px
  chip-accent:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.full}"
    padding: 4px 12px
  stat:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.stat}"
  caption:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface-muted}"
    typography: "{typography.body-sm}"
  nav:
    backgroundColor: "{colors.background}"
    textColor: "{colors.on-background}"
    typography: "{typography.label-lg}"
    height: 72px
  footer:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-sm}"
    padding: 64px 24px
  badge-success:
    backgroundColor: "{colors.success}"
    textColor: "{colors.on-success}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.full}"
    padding: 4px 10px
  alert-error:
    backgroundColor: "{colors.error}"
    textColor: "{colors.on-error}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 16px
  divider:
    backgroundColor: "{colors.outline}"
    height: 1px
  icon-muted:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface-muted}"
    size: 24px
---

# Swasthya Cream and Brown Design System

## Overview

Swasthya uses a warm cream field and brown-only interface accents. Food photography may keep natural greens. UI chrome, buttons, links, charts and focus states do not.

## Colors

A calm, nature-based palette: cream for space, brown for structure and action.

- **Cream (#FAF7EE):** primary page background.
- **Soft cream (#F3EBDD):** secondary surfaces, tracks and muted panels.
- **Off-white (#FFFDF8):** cards and form surfaces.
- **Primary brown (#5B4636):** primary buttons, progress, selected controls.
- **Dark brown (#463326):** headings, high-contrast text and hover states.
- **Medium brown (#7A5C46):** secondary text, links and supporting accents.
- **Light brown (#A68A72):** muted icons and quieter details.
- **Beige (#E5D8C6):** borders, dividers and input outlines.

Interface tokens live in `frontend/src/index.css` `:root`. Components should use those semantic variables rather than new hex values.

## Typography

**Cormorant Garamond** SemiBold for headlines and the product name. **Karla** for body copy, forms, navigation and supporting text.

## Layout

Public landing, authentication, profile, log meal and dashboard share one cream canvas. Cards, beige panels and the translucent navbar create hierarchy without switching the page colour. Spacing is built on 8px. Layouts stay as designed; this palette does not introduce a new information architecture.

## Elevation & Depth

Flat and warm. Photos, cards and the navbar carry depth with a soft brown-tinted shadow; the rest uses thin beige rules and cream or off-white surfaces.

## Shapes

Rounded cards (about 22px) and pill-shaped buttons and fields. Decorative leaf marks on authentication screens use primary brown at low opacity.

## Components

- **Primary button:** primary brown with cream text; hover uses dark brown.
- **Secondary button:** cream background, brown text and a beige border.
- **Navbar:** translucent cream; active text links use dark brown with a brown underline; Login / Sign Up stays a filled primary button.
- **Cards:** warm off-white with beige borders.
- **Progress:** primary brown fill on a beige track.
- **Success:** brown styling plus labels or check icons; colour is not the only signal.
- **Error:** rust `#7A4538` with copy, so failure stays distinct from success without using green.

## Do's and Don'ts

- Do keep cream as the page background on every screen.
- Do use brown for interactive accents, charts, focus rings and selected controls.
- Don't introduce green UI chrome, even for success states.
- Don't recolour genuine food photography.
