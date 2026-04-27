---
version: alpha
name: Labmix
description: A clean, professional, and data-driven design system for the RCI management platform.
colors:
  primary: "#fffcff"
  inverted: "#28282b"
  secondary: "#f2f2f2"
  tertiary: "#96e6b3"
  surface: "#efefef"
  text: "#0d2818"
  border: "#627264"
  accent: "#627264"
  glass: "rgba(140, 175, 156, 0.3)"
  red: "#ef3054"
  green: "#96e6b3"
  blue: "#97d2fb"
  yellow: "#ffd54f"
typography:
  main:
    fontFamily: "Chivo, sans-serif"
    fontSize: "16px"
  secondary:
    fontFamily: "IBM Plex Mono, monospace"
    fontSize: "14px"
rounded:
  default: "8px"
  sm: "4px"
  md: "8px"
  lg: "12px"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2rem"
---

# SAM Design System

## Overview
The SAM design system is built to provide a clean, professional, and efficient user experience for managing data-intensive workflows. The aesthetic focuses on clarity, readability, and a soft, modern palette that reduces cognitive load.

## Colors
The palette is dominated by off-whites and soft greens, creating a "breathable" interface.
- **Primary**: Used for main backgrounds and large surfaces.
- **Tertiary/Green**: The signature color for positive actions and success states.
- **Accent**: Used for borders, labels, and secondary interactive elements to provide structure.
- **Inverted**: Reserved for high-contrast text and dark-mode-like elements.

## Typography
- **Main (Chivo)**: Used for all UI text, headers, and body content. It offers excellent legibility at small sizes.
- **Secondary (IBM Plex Mono)**: Used for technical data, numbers, and code-like snippets where fixed-width alignment is beneficial.

## Layout
The system follows a flexible grid with standard breakpoints:
- **Desktop (1920px)**: 2rem horizontal padding.
- **Tablet (768px)**: 1rem horizontal padding.
- **Mobile (480px)**: 0.5rem horizontal padding.

## Elevation & Depth
- **Glassmorphism**: Used in overlays and modals via `backdrop-filter: blur(1px)` and semi-transparent backgrounds.
- **Shadows**: Subtle shadows are applied on hover to interactive elements like buttons and cards to provide depth.

## Shapes
A consistent **8px corner radius** is applied across all primary components (Buttons, Inputs, Modals, Cards) to maintain a soft but structured look.

## Animations
The system uses smooth, subtle transitions to enhance the feeling of responsiveness.
- **Transitions**: Standard `0.3s ease` for most state changes (hover, focus, toggle).
- **Shimmer**: A 1.5s infinite linear gradient animation used in loading states to indicate active processing.

## Components

### Buttons
- **Primary**: Green background, 8px radius, text-color text.
- **Delete**: Red background, primary-color text.
- **Ghost**: Light red background with a red border, typically for secondary negative actions.
- **Hover State**: Elevates with a multi-layered shadow.

### Input Forms
- **Field**: 8px radius, green border by default.
- **Focus State**: Transitions border to accent-color with a subtle glow shadow.
- **Disabled State**: Reduced opacity (0.6) with a gray background.

## Do's and Don'ts
- **Do**: Use variable tokens (e.g., `var(--green-color)`) instead of hardcoding hex values.
- **Do**: Maintain the 8px radius for all new container elements.
- **Don't**: Use sharp corners unless explicitly required by technical constraints.
- **Don't**: Overuse saturated colors; stick to the soft palette for long-term user comfort.
