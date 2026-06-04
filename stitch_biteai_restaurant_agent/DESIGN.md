---
name: BiteAI
colors:
  surface: '#111318'
  surface-dim: '#111318'
  surface-bright: '#37393f'
  surface-container-lowest: '#0c0e13'
  surface-container-low: '#1a1b21'
  surface-container: '#1e1f25'
  surface-container-high: '#282a2f'
  surface-container-highest: '#33353a'
  on-surface: '#e2e2e9'
  on-surface-variant: '#e3bdc0'
  inverse-surface: '#e2e2e9'
  inverse-on-surface: '#2e3036'
  outline: '#aa888b'
  outline-variant: '#5b4042'
  surface-tint: '#ffb2ba'
  primary: '#ffb2ba'
  on-primary: '#670020'
  primary-container: '#ff4f73'
  on-primary-container: '#5a001b'
  inverse-primary: '#bd0042'
  secondary: '#ffd799'
  on-secondary: '#432c00'
  secondary-container: '#feb300'
  on-secondary-container: '#6a4800'
  tertiary: '#ffb4a5'
  on-tertiary: '#650b00'
  tertiary-container: '#ff5637'
  on-tertiary-container: '#590800'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffd9dc'
  primary-fixed-dim: '#ffb2ba'
  on-primary-fixed: '#400011'
  on-primary-fixed-variant: '#910031'
  secondary-fixed: '#ffdeac'
  secondary-fixed-dim: '#ffba38'
  on-secondary-fixed: '#281900'
  on-secondary-fixed-variant: '#604100'
  tertiary-fixed: '#ffdad3'
  tertiary-fixed-dim: '#ffb4a5'
  on-tertiary-fixed: '#3e0400'
  on-tertiary-fixed-variant: '#8e1300'
  background: '#111318'
  on-background: '#e2e2e9'
  surface-variant: '#33353a'
typography:
  display-lg:
    fontFamily: Outfit
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Outfit
    fontSize: 28px
    fontWeight: '600'
    lineHeight: '1.2'
  title-md:
    fontFamily: Outfit
    fontSize: 20px
    fontWeight: '500'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: 0.05em
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-padding-mobile: 20px
  container-padding-desktop: 40px
  gutter: 16px
  stack-sm: 8px
  stack-md: 24px
  stack-lg: 48px
---

## Brand & Style
The design system is engineered to evoke a sense of "culinary intelligence"—combining the precision of high-end AI with the vibrant, sensory experience of fine dining. The target audience consists of urban epicureans and tech-forward travelers who seek curated, premium experiences without the friction of endless searching.

The visual style is a refined execution of **Glassmorphism**, leveraging deep, layered transparency to create a sense of infinite digital space. It prioritizes a "Dark Mode First" architecture, using high-fidelity glows and vibrant red-to-orange gradients to draw the eye toward actionable recommendations. The overall aesthetic is sleek, immersive, and unmistakably premium, positioning the product as a sophisticated concierge rather than a simple search tool.

## Colors
This design system utilizes a foundation of deep, nocturnal tones to allow the vibrant food photography and brand accents to radiate. 

- **Primary & Accents:** The core brand energy is driven by a high-octane red-to-orange gradient, used for primary actions and "hot" recommendations. 
- **Functional Accents:** Gold is reserved exclusively for ratings and "Premium" status indicators, ensuring clear value signaling. 
- **Surface Strategy:** The background is a solid Deep Charcoal (#0b0d12). Overlays and containers use a translucent Slate-Navy with a 10px backdrop blur, creating a "frosted glass" hierarchy that maintains legibility while feeling lightweight.
- **Typography Colors:** Primary text uses off-white for maximum contrast, while secondary metadata and captions utilize a muted blue-gray (#94a3b8) to reduce visual noise.

## Typography
The typography strategy centers on high-contrast weights to establish a clear information hierarchy. **Outfit** is used for headlines and titles to provide a geometric, modern flair that feels tech-centric. **Inter** is employed for body text and labels to ensure maximum readability during long-form reviews or menu browsing.

Use "Display-lg" sparingly for hero marketing moments. "Label-caps" should be used for category tags (e.g., CUISINE TYPE) to provide a structural, organized feel. Headlines should always use the "Bold" or "Semi-Bold" weights to stand out against the soft, blurred backgrounds of the glassmorphic containers.

## Layout & Spacing
The layout follows a **Fluid Grid** model with an 8px base increment. For desktop, a 12-column grid is utilized with 24px gutters to allow for expansive, high-resolution food imagery. On mobile devices, the system collapses to a single-column layout with 20px side margins.

Spacing should be generous to maintain a "premium" feel; avoid crowding elements. Use the "stack-lg" (48px) to separate major sections, and "stack-sm" (8px) for internal component spacing, such as the distance between an icon and a label. Components like cards should use internal padding of at least 24px to ensure the glassmorphic "depth" has room to breathe.

## Elevation & Depth
Depth in the design system is achieved through light and transparency rather than traditional heavy shadows. 

1.  **The Base:** The solid #0b0d12 background serves as the deepest layer.
2.  **The Glass Layer:** Floating cards use `rgba(18, 23, 37, 0.6)` with a `backdrop-filter: blur(10px)`.
3.  **The Stroke:** To define edges on dark backgrounds, every glass container must have a 1px solid border. Use a top-down gradient for this border: `rgba(255, 255, 255, 0.15)` at the top to `rgba(255, 255, 255, 0.05)` at the bottom.
4.  **The Glow:** Active states or "Featured" cards utilize a subtle outer glow (box-shadow) using the primary brand color at 20% opacity and a 20px blur radius. This creates a "neon-on-glass" effect.

## Shapes
The design system employs a **Rounded** shape language to feel approachable and modern.

- **Standard Containers:** Cards and input fields use a 0.5rem (8px) corner radius.
- **Large Elements:** Featured recommendation hero cards use 1.5rem (24px) to feel distinct and substantial.
- **Interactive Elements:** Buttons and Segmented Controls are strictly **Pill-shaped** (full radius), providing a clear tactile distinction from informational cards.
- **Imagery:** Profile pictures and rating badges should be circular.

## Components

### Buttons & Controls
- **Primary Action:** Pill-shaped with the brand gradient. Text is white, bold. On hover, the gradient should shift slightly in hue or increase in brightness.
- **Segmented Pills:** Used for filters (e.g., "Price," "Distance"). Unselected states are transparent with a thin border; selected states take on the primary gradient.
- **Sliders:** Minimalist track (#1e293b) with a primary gradient thumb.

### Cards (Featured Recommendations)
- **Structure:** A glassmorphic base container. The top 60% is a high-quality image with a subtle bottom-to-top dark gradient overlay for text legibility.
- **Details:** The bottom 40% contains the restaurant name (Outfit Bold), rating (Gold icon + text), and price level.
- **Interactive:** The entire card has a subtle hover lift effect (Y-axis -4px).

### Input Fields & Dropdowns
- **Inputs:** Dark translucent fill with a subtle 1px border. On focus, the border glows with the primary color.
- **Dropdowns:** Glassmorphic menus that "float" above the UI, using a higher backdrop blur (20px) to ensure separation from the content below.

### Rating Indicators
- **Style:** A solid gold star icon followed by a bold Outfit-font number. For AI-specific confidence scores, use a secondary circular progress ring around the rating.