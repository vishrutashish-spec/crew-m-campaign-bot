# CleverTap Campaign Setup Skill — Plum Implementation Guide

> How Plum actually builds and configures campaigns in CleverTap. Covers email
> templates, push notifications, WhatsApp messages, design patterns, deeplinks,
> and mobile/desktop visibility rules.
>
> This is the practical "how to set it up in the tool" companion to
> CLEVERTAP_PLATFORM_REFERENCE.md (which covers what the platform can do).

---

## 1. Deeplinks Reference

All CTAs in Plum campaigns point to deeplinks that route users into the correct
app screen. These are the canonical deeplinks:

| Destination | Deeplink |
|-------------|----------|
| App home / login | `https://deeplink.plumhq.com/home` |
| Claims | `https://deeplink.plumhq.com/claims` |
| Telehealth home | `https://deeplink.plumhq.com/care` |
| Benefits page | `https://deeplink.plumhq.com/benefits` |
| Health Risk Assessment | `https://deeplink.plumhq.com/home?screen=hra` |
| Health Checkup home | `https://deeplink.plumhq.com/home?screen=hc` |

**Rules:**
- Always use the deeplink, never a raw app URL or web fallback
- The deeplink handles both app-installed (opens in-app) and no-app (redirects
  to web/store) cases
- Button "Action" in CleverTap editor: set to "Open web page" with the deeplink
  as the URL
- Image links also use deeplinks (e.g. banner image linking to HRA screen)

---

## 2. Email Template Setup

### 2.1 Template Architecture — The 12-Grid System

Plum emails use CleverTap's drag-and-drop editor with a **12-column grid**.
The template is structured as stacked rows, where each row contains content
blocks (images, text, buttons) arranged within the 12-column grid.

**Standard email structure (top to bottom):**

```
┌─────────────────────────────────────┐
│  Header Banner Image (full width)   │  ← Desktop version
├─────────────────────────────────────┤
│  Header Banner Image (full width)   │  ← Mobile version (hidden on desktop)
├─────────────────────────────────────┤
│  Body Text                          │
│  (personalization, copy, bullets)   │
├─────────────────────────────────────┤
│  Content Images (2-col or full)     │
├─────────────────────────────────────┤
│  CTA Button                        │  ← Desktop version
├─────────────────────────────────────┤
│  CTA Button                        │  ← Mobile version (hidden on desktop)
├─────────────────────────────────────┤
│  Closing copy + sign-off           │
├─────────────────────────────────────┤
│  Footer — Desktop                  │  ← Hidden on mobile
├─────────────────────────────────────┤
│  Footer — Mobile                   │  ← Hidden on desktop
├─────────────────────────────────────┤
│  App Download — Desktop            │  ← Hidden on mobile
├─────────────────────────────────────┤
│  App Download — Mobile             │  ← Hidden on desktop
├─────────────────────────────────────┤
│  Unsubscribe link                  │
└─────────────────────────────────────┘
```

### 2.2 Mobile/Desktop Visibility — The "Hide On" Pattern

This is the most important pattern in Plum's email setup. CleverTap's editor
has a **"Hide on"** toggle at the bottom of every content block's properties
panel, with three icons: desktop, tablet, mobile.

**Why duplication is necessary:**

Email rendering differs drastically between desktop and mobile clients. Rather
than relying on responsive CSS (which many email clients strip), Plum creates
**two versions of key blocks** and uses "Hide on" to show the right one:

| Block | Desktop version | Mobile version |
|-------|----------------|----------------|
| Header banner | 944 × 422px, side-by-side layout | 514 × 828px, stacked layout |
| CTA button | Sized for desktop width | Sized for mobile width |
| Footer | Horizontal: logo + social icons in one row | Stacked: logo above, social below |
| App download | Side-by-side App Store + Google Play | Stacked badges |

**How to configure:**
1. Create the desktop version of the block
2. Duplicate it (use the copy icon in the block toolbar)
3. Redesign the duplicate for mobile
4. On the desktop version: "Hide on" → toggle mobile ON (hidden on mobile)
5. On the mobile version: "Hide on" → toggle desktop ON (hidden on desktop)

**Default state:** "Hide on" is OFF for all three (desktop/tablet/mobile),
meaning the block shows everywhere. You must explicitly toggle.

### 2.3 Header Banner Images

**Desktop banner:** 944 × 422px
- Full-width image
- Contains: Plum logo (top-left), headline text (large, serif if brand font),
  subheadline, phone mockup showing app screen, CTA button baked into image
- Image hosted on CloudFront: `d250yozwgs1tp8.cloudfront.net/...`
- Image link: set to the campaign's deeplink (e.g. HRA deeplink)
- Image rounded corners: 0 (full bleed)
- Padding: 0 on all sides

**Mobile banner:** 514 × 828px
- Same content as desktop, but laid out vertically (stacked)
- Plum logo centered at top
- Headline centered below
- Phone mockup larger and centered
- Hidden on desktop via "Hide on" toggle

**Important:** Banner text is baked into the PNG — it is NOT live HTML text.
This means any font (including GT Alpina) renders correctly because it's
pixels, not a web font the email client would need to load.

### 2.4 Body Text

**Personalization tag format:**
```
*|Profile - warehouse_production_firstName [there]|*
```

- `Profile - warehouse_production_firstName` = the CT user property
- `[there]` = fallback value if the property is empty
- Wrapped in `*|...|*` delimiters (CleverTap's personalization syntax)

**Example opening:**
```
Hi *|Profile - warehouse_production_firstName [there]|*,

Most health issues don't show symptoms right away. By the time you
notice something's wrong, it's often been building for years. That stops now.
```

**Body text settings:**
- Font: Global font (maps to the template's base font, typically Inter or
  system sans-serif)
- Font size: 16px (body), 18px (buttons)
- Text color: dark (not pure black — matches Plum's brand)
- Line height: 1.5
- Text direction: LTR

**Bold text for emphasis:** Used sparingly for key sentences, e.g.:
"**This comprehensive health checkup is already available for you through
[OrgName], so please don't let it go unused.**"

### 2.5 Content Images (Inline)

For explanatory content (e.g. "How to book" steps, "What you get" features),
Plum uses inline images:

**Two-column layout (6+6 grid):**
- Two images side by side, each showing a phone mockup
- Descriptive text below each image
- Used for feature showcases (e.g. Health Score screen + Goal selection screen)

**Four-step "How to book" pattern:**
- 2×2 grid of numbered step images (01, 02, 03, 04)
- Each step: phone screenshot with numbered overlay
- Caption text below each: "Go to 'Benefits' in your Plum app", etc.

**Image properties:**
- Hosted on CloudFront CDN
- Rounded corners: 0 (default)
- Padding: 0
- Image link: deeplink to the relevant screen

### 2.6 CTA Buttons

**Button styling (Plum standard):**

| Property | HRA emails | HC emails |
|----------|-----------|-----------|
| Background color | `#571541` (plum purple) | `#ee4f5e` (coral/red) |
| Text color | `#ffffff` | `#ffffff` |
| Font | Global font | Global font |
| Font weight | Regular | Regular |
| Font size | 18px | 18px |
| Border radius | 8px | 8px |
| Content padding | 13px top/bottom, 16px left/right | 13px top/bottom, 16px left/right |
| Auto width | ON | ON |
| Align | Center | Center |
| Line height | 1.5 | 1.5 |
| Letter spacing | 0 | 0 |
| Border | None (solid, 0, transparent) | None |

**Button text examples:**
- "Take the health risk assessment"
- "Book your free health checkup"
- "Download the Plum app"

**Button URL:** Always a deeplink (see Section 1).

**Desktop/mobile duplication:**
Buttons are duplicated — one for desktop, one for mobile — with "Hide on"
toggles. This ensures proper sizing on both. The mobile button may have
slightly different padding or width behavior.

### 2.7 Footer

The footer is **fixed artwork** — same across all emails, never modified per
campaign.

**Desktop footer (hidden on mobile):**
- Row 1: Plum wordmark (left) + social icons X, Instagram, LinkedIn (right)
- Horizontal layout

**Mobile footer (hidden on desktop):**
- Plum wordmark centered
- Social icons centered below
- Stacked layout

**App download section:**
- Desktop: "Download the Plum app" text + App Store and Google Play badges
  side by side
- Mobile: Same but stacked vertically
- Again, two versions with "Hide on" toggling

**Unsubscribe:**
- Always at the very bottom
- Text: "If you'd rather not receive this kind of email, unsubscribe here"
- "here" links to CleverTap's unsubscribe URL (special link)

### 2.8 Sign-off

Standard sign-offs:
- "With care, Team Plum" (for health/wellness emails)
- "With Care, Team Plum" (capitalized variant)
- "Plum Claims Team" (for claims-related emails)
- "Team Plum" (general)

Always preceded by a warm closing line:
- "Give yourself a minute today. You deserve it."
- "We'd love for you to book it soon."

### 2.9 Sender Details

| Field | Value |
|-------|-------|
| Sender name | Plum |
| From address | updates@info.plumhq.com |
| Reply-to | care@plumhq.com |

---

## 3. Push Notification Setup

### 3.1 Template Selection

In CleverTap: Messages > Campaigns > + Campaign > Push Notification

Select the **Standard** template (not rich media or custom) for most Plum
notifications.

### 3.2 Content Structure

| Field | Limit | Plum Convention |
|-------|-------|-----------------|
| Title | 30–40 chars (design for 30) | Literal for functional, light hook for delight |
| Body | 90–120 chars | One idea, one sentence, no sub-clauses |
| Image | Optional (rich push) | Use sparingly — only when visual adds value |
| Deep link | Required | Use deeplinks from Section 1 |
| Custom KV pairs | Optional | For tracking, analytics routing |

### 3.3 Functional vs Delight Push

**Functional** (claims, policy, booking, payment):
- Title: literal ("Your claim is approved", "Checkup booked for 24 August")
- Body: next action or what happens next
- No wordplay, no puns, no humor
- No emoji in body; at most one emoji in title for tone signaling

**Delight** (engagement, feature discovery, wellness):
- Title: can carry a light hook
- Body: one sentence adding the next piece of info
- Hook must land without needing the body to explain it
- If the joke doesn't fit in 30 chars, it's an email joke, not a push joke

### 3.4 Push Setup Steps in CleverTap

1. **Start Here:** Select qualification (Past behavior / Live / External trigger)
2. **Who:** Define audience segment
3. **What:** Click "Go To Editor"
   - Enter Title
   - Enter Body
   - Set Deep Link URL (Advanced > On Click > Deep Link)
   - Optional: Add image URL for rich push
   - Optional: Add action buttons (up to 3)
   - Optional: Add custom key-value pairs
   - Preview on Android/iOS
   - Send test to test profiles
4. **When:** Schedule or trigger
5. **Publish**

### 3.5 Action Buttons (Optional)

Up to 3 buttons per push notification:
- Each button has: Label (text), Action (deeplink or dismiss), Icon (optional)
- Keep labels under 15 characters
- Primary action should match the body's intent

---

## 4. WhatsApp Message Setup

### 4.1 Prerequisites

- WhatsApp is a paid add-on in CleverTap
- Template must be pre-approved by Meta before sending
- User must be opted in (`MSG-whatsapp: true` on their profile)
- Templates are managed at: Settings > Channels > WhatsApp > [Provider] > Templates

### 4.2 Template Structure

| Component | Limit | Notes |
|-----------|-------|-------|
| Header (text) | 60 chars | Alternative: image/video/document/location |
| Body | 1,024 chars | Includes personalization variables |
| Footer | 60 chars | Static text, no variables |
| Quick Reply buttons | Up to 3 | 20 chars each (safe target) |
| CTA buttons | Up to 2 | Phone number or URL |

### 4.3 Template Types

**Standard Text:** Header text + body + footer + buttons

**Media Template:** Image/video/document as header + body + footer + buttons.
Preferred for engagement campaigns (visual impact on chat surface).

**Interactive Template:** Body + Quick Reply buttons (up to 3) or CTA buttons
(up to 2). Quick Reply buttons let users respond with one tap.

### 4.4 Personalization in Templates

WhatsApp templates use numbered placeholders:
```
Hi {{1}}, your health checkup with {{2}} is confirmed for {{3}}.
```

- `{{1}}` = mapped to a CT user property (e.g. first name)
- Variables are set per-template in CleverTap's template configuration
- Fallback values configured in the campaign editor

### 4.5 WhatsApp Setup Steps in CleverTap

1. **Create template** in WhatsApp BSP (or CleverTap if using CT BSP)
2. **Wait for Meta approval** (can take minutes to hours)
3. **Sync template** to CleverTap: Settings > WhatsApp > Templates > Sync
4. **Create campaign:** Messages > Campaigns > + Campaign > WhatsApp
5. **Start Here:** Set qualification and conversion goal
6. **Who:** Define audience (must be opted in for WhatsApp)
7. **What:** Select the approved template
   - Map personalization variables to CT profile/event properties
   - Configure media header if applicable
   - Set Quick Reply / CTA button actions
   - Preview and test
8. **When:** Schedule
9. **Publish**

### 4.6 Plum WhatsApp Conventions

- Lead with personalization: "Hi {{1}}," (name or "there" fallback)
- One clear CTA — don't compete with multiple asks
- Keep conversational — chat surface, not email
- Benefit-led, not mechanism-led
- End with a single CTA button ("Book now", "Check your score", "View benefits")

---

## 5. In-App Notification Setup

### 5.1 Template Types

| Type | Use Case |
|------|----------|
| Header | Top banner, dismissible, minimal disruption |
| Footer | Bottom banner, good for persistent nudges |
| Half-interstitial | Takes half the screen, for medium-priority messages |
| Interstitial | Full-screen takeover, for high-priority (use sparingly) |
| Cover | Full-screen with background image |
| Custom HTML | Fully custom layout (advanced) |

### 5.2 Setup Steps

1. Messages > Campaigns > + Campaign > In-App
2. **Who:** Must be a Live User Segment (in-app triggers require the user to
   be in the app)
3. **What:** Select template type > Go To Editor
   - Set title, body, image, CTA
   - Configure display rules (trigger event, display frequency)
   - Set dismiss behavior
4. **When:** Set start/end dates (runs continuously while active)

### 5.3 Trigger Events

In-app notifications fire when a user performs a specific event while the app
is open. Common Plum triggers:
- `App Launched` — show on app open
- `pathViewed` with property filter — show on specific screen
- `healthCheckupbooking_confirmed` — post-action confirmation

---

## 6. Campaign Editor Patterns — Quick Reference

### 6.1 Content Block Toolbar

Every content block (image, text, button, etc.) has a floating toolbar:
- **Delete** (trash icon) — removes the block
- **Duplicate** (copy icon) — creates an identical block below

Use Duplicate extensively for the desktop/mobile visibility pattern.

### 6.2 Block Properties Panel (Right Side)

When a block is selected, the right panel shows:

**For Images:**
- Align (left / center / right)
- Apply effects / Change image
- URL (image source)
- Alt text
- Image rounded corners
- ACTION: Image link type + URL
- BLOCK OPTIONS: Padding, Hide on

**For Buttons:**
- URL (button link)
- BUTTON OPTIONS: Auto width, Font family, Font weight, Font size,
  Background color, Text color, Align, Line height, Letter spacing,
  Text direction, Border radius, Content padding, Border
- BLOCK OPTIONS: Padding, Hide on

**For Text:**
- Rich text editor toolbar (Bold, Italic, Underline, Strikethrough, etc.)
- Font size, alignment, lists, text color, highlight
- Special links, Personalization insertion
- BLOCK OPTIONS: Padding, Hide on

### 6.3 Row-Level Controls

Rows (horizontal sections) have their own settings:
- Background color
- Background image
- Content area width
- Column layout (1-col, 2-col, 3-col, 4-col within 12-grid)
- Padding
- Hide on (desktop/tablet/mobile)

### 6.4 Template-Level Settings

Under the **SETTINGS** tab (top-right):
- Email width (default: 600px for desktop compatibility)
- Background color (outer)
- Content area background color
- Default font
- Link color
- Preheader text

---

## 7. Image Hosting

All images in Plum emails are hosted on CloudFront CDN:

| CDN Domain | Usage |
|------------|-------|
| `d250yozwgs1tp8.cloudfront.net` | Email assets (banners, illustrations) |
| `d1qzvqecfo5h8o.cloudfront.net` | Product images (app screenshots, mockups) |

Images are uploaded through CleverTap's built-in image manager or referenced
by URL. CleverTap also hosts uploaded images on its own CDN.

---

## 8. Testing Before Send

### 8.1 Email Testing Checklist

1. **Preview desktop + mobile** using the toggle icons (desktop/mobile) in the
   editor's top-left
2. **Check "Hide on" logic:** Verify that desktop-only blocks are hidden on
   mobile preview and vice versa
3. **Check personalization:** Use "Preview & Test" to send a test email to a
   test profile — verify that `*|Profile - ...|*` tags resolve correctly
4. **Check deeplinks:** Click every button/image link in the test email to
   verify it routes to the correct app screen
5. **Check fallbacks:** Test with a profile that has no first name — verify
   the fallback (e.g. "there") renders
6. **Check footer:** Verify unsubscribe link works, app download badges are
   correct, social icons link correctly

### 8.2 Push Testing

1. Use "Preview & Test" in the What section
2. Select a test profile or enter a device token
3. Verify title + body render correctly on the test device
4. Verify deep link opens the correct screen
5. Test on both Android and iOS if possible

### 8.3 WhatsApp Testing

1. Send test to a profile marked as test profile
2. Verify personalization variables resolve
3. Verify media renders (if media template)
4. Verify Quick Reply / CTA buttons work
5. Check that the template hasn't been rejected by Meta

---

## 9. Common Mistakes to Avoid

1. **Forgetting to set "Hide on"** — results in duplicate content visible on
   both desktop and mobile (user sees two banners, two buttons, two footers)

2. **Using web URLs instead of deeplinks** — the user lands on a web page
   instead of the app screen. Always use `deeplink.plumhq.com/...`

3. **Not testing personalization fallbacks** — if the user property is empty
   and no fallback is set, the tag renders as blank or as the raw tag text

4. **Leaving placeholder copy** — "Heading that fits in 2 lines" or
   "Button CTA in 4-5 words" shipping in production

5. **Wrong image dimensions** — desktop banner at 944×422, mobile at 514×828.
   Using the wrong size causes stretching or cropping

6. **Modifying the footer** — the footer is fixed artwork. Don't change
   colors, layout, or content

7. **Not setting conversion goal** — set it in "Start Here" before publishing.
   Without it, you have no conversion attribution data

8. **WhatsApp without opt-in** — messages to users without `MSG-whatsapp: true`
   will fail silently

---

## 10. Campaign Naming Convention

Use a consistent naming pattern for campaigns in CleverTap:

```
[Channel] [Objective] [Audience] [Date] [Version]
```

Examples:
- `Email HRA Activation All Users Aug2026 v1`
- `Push HC Booking Reminder Active Users Aug2026`
- `WhatsApp TH Reengagement Dormant Users Aug2026 AB`

This makes campaigns searchable and filterable in CleverTap's campaign list.

---

## 11. Email Visual Design System — Extracted from Production Emails

> Audited from live Plum emails: "Introducing the Plum CD account",
> "1% healthier, everyday" (Day 2 onboarding), and "Investigating Heart
> Disease" (Data Labs). These patterns are the ground truth for how Plum
> emails look and feel.

### 11.1 Typography

| Element | Font | Size | Weight | Color | Line Height |
|---------|------|------|--------|-------|-------------|
| Banner headline (baked into image) | GT Alpina (serif) | Large (varies) | Bold | White or dark plum | — |
| Body text | Inter / system sans-serif | 16px | Regular (400) | Dark plum `#571541` | 1.5–1.6 |
| Section sub-header | Inter | 16–18px | Bold (700) | Dark plum or coral `#ee4f5e` | 1.4 |
| Bold lead-in within list | Inter | 16px | Bold (700) | Dark plum | 1.5 |
| CTA button text | Inter | 18px | Regular (400) | White `#ffffff` | 1.5 |
| Footer / legal text | Inter | 12–13px | Regular | Muted gray | 1.4 |

**Key rules:**
- Body text is **never pure black** — always dark plum/maroon (`#571541`)
- GT Alpina (serif) is used for display-level headlines only, and always
  baked into banner images (not live HTML text, because email clients
  cannot load custom web fonts reliably)
- Italic serif is used for emphasis words in headlines ("1% healthier,
  *everyday*")
- Bold is used sparingly within body: for key phrases ("**Plum health and
  wellness benefits are funded and activated**") and for lead-in labels
  in numbered lists ("1. **Instant activation**: When you add...")
- Bold lead-ins are followed by a colon, then regular weight continues
  on the same line — never an all-bold paragraph

### 11.2 Spacing System

**Vertical spacing (top to bottom):**

| Gap | Measurement | Where |
|-----|-------------|-------|
| Banner → first body text | 24–32px | After header image to opening "Hi [name]" |
| Between paragraphs | 16–20px | Between body text blocks (≈ 1 line-height) |
| Between major sections | 32–40px | E.g. "What's getting better" → "The one change you need to make" |
| Section header → its content | 8–12px | Sub-header to the first line of that section |
| Before CTA button | 24–32px | Breathing room above the primary action |
| After CTA button | 24–32px | Before closing copy or next section |
| Body → sign-off | 32–40px | "Regards, Prayat Shah" or "With care, Team Plum" |
| Sign-off → footer | 40–48px | Clear separation before the fixed footer artwork |

**Horizontal spacing:**

| Context | Left/Right Padding |
|---------|-------------------|
| Desktop content area | 32–40px each side |
| Mobile content area | 16–20px each side |
| CTA button internal | 16px horizontal, 13px vertical |

**General principles:**
- Generous whitespace between sections — emails breathe, never feel packed
- Major thematic shifts get a **coral divider line** (1–2px, full content
  width) plus extra vertical space
- Bullet lists and numbered lists have consistent indent and spacing
  between items

### 11.3 Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| Dark plum | `#571541` | All body text, plum-variant CTA buttons |
| Coral/red | `#ee4f5e` | Accent CTAs, links, divider lines, Data Labs branding |
| White | `#ffffff` | Content area background, button text |
| Soft pink | `#FFBFC5` | Header banner backgrounds (onboarding emails) |
| Light gray | `#f5f5f5` – `#f0f0f0` | Outer email background (visible in inbox apps around the white content) |

**Color application rules:**
- **Text** is always dark plum — never black, never gray
- **Links** are coral/red, matching the accent CTAs
- **CTA buttons** use either plum (HRA, product) or coral (HC, engagement,
  Data Labs) — never both in the same email
- **Divider lines** between sections are always coral/red, thin (1–2px)
- **Background** of the content area is always white; outer email
  background (the strip visible in some clients) is light gray or white

### 11.4 Button Design

**Two CTA color variants:**

| Variant | Background | Use for |
|---------|-----------|---------|
| Plum | `#571541` | HRA, product feature, benefits |
| Coral | `#ee4f5e` | Health checkup, engagement, Data Labs |

**Button specs (both variants):**

| Property | Value |
|----------|-------|
| Text color | `#ffffff` |
| Font size | 18px |
| Font weight | Regular (400) |
| Border radius | 8px (moderate, not pill-shaped) |
| Padding | 13px top/bottom, 16px left/right |
| Alignment | Centered in content column |
| Width | Auto (fits text) |
| Border | None |

**Button text patterns:**
- Action verb + what they'll get: "Take the health risk assessment"
- Short and direct: "Book your free health checkup"
- With arrow for directional cue: "Speak to us →"
- **One primary CTA per email** — never multiple competing buttons
  (exception: "Download the Plum app" in footer is secondary, not
  competing)

**CTA card pattern (alternative to buttons):**
The "1% healthier" onboarding email uses bordered card CTAs instead of
filled buttons for multiple options within a section:
- Thin border container
- Coral/red text (not white-on-color)
- Small icon on the right side of the card
- Used when offering 2–3 related choices within one section
  (e.g. "Sign up for a Cult.fit membership", "Book a physiotherapy
  session")
- These are **not primary CTAs** — they're secondary actions within a
  content section

### 11.5 Layout Patterns

**Single column always:**
- Content is never laid out in side-by-side columns for body text
- Max content width: 600px (email standard)
- Header images go full-bleed (edge-to-edge within the 600px container)
- Body text, buttons, and sign-offs are inset with the padding above

**Vertical stacking order (standard template):**
1. Full-width header banner (with baked-in headline + visuals)
2. Greeting with personalization
3. Opening paragraph
4. Body sections with sub-headers
5. Numbered/bulleted list (if applicable)
6. Primary CTA button (centered)
7. Closing copy
8. Personal sign-off ("Regards, Prayat Shah" or "With care, Team Plum")
9. Footer (dual desktop/mobile versions via "Hide on")
10. App download badges
11. Unsubscribe link

**Section dividers:**
- Used between major thematic sections
- Coral/red thin line (1–2px)
- Full content width (within padding)
- **Not** used between every paragraph — only at thematic shifts

### 11.6 Template Archetypes

From the audited emails, three distinct template archetypes:

**1. Product Announcement (CD Account email)**
- Illustrated header banner (scenic, artistic — not a screenshot)
- Plum logo in banner
- Long-form body with multiple sections
- Numbered list for feature breakdown
- Bold lead-ins: "1. **Instant activation**: ..."
- Plum purple CTA button
- Professional sign-off

**2. Engagement / Onboarding Series (Day 2 email)**
- Branded header: "Day 2 of plum" in coral
- Serif headline with italic emphasis word
- Phone mockup showing app notification
- Coral divider lines between sections
- Section headers in large serif (GT Alpina, baked into image or
  styled as display text)
- CTA cards (bordered containers, not filled buttons) for multiple
  action options
- Grouped by theme: "Get moving", "Feed yourself better",
  "Learn something useful"
- "PLUM STORIES" badge for content links

**3. Data / Research (Data Labs email)**
- Full-bleed coral/red header with bold uppercase headline
- "plum DATA LABS" branding
- Personal sign-off from a named leader ("Prayat Shah, Head of
  Healthcare at Plum")
- External links (datalabs.plumhq.com)
- Bullet list for data findings
- Single coral CTA: "Speak to us →"
- Academic/authoritative tone, still warm

### 11.7 Mobile Rendering Observations

From the CT editor mobile preview:
- Content blocks reflow correctly within the narrower viewport
- Images scale to fit
- Buttons are full-width or near-full-width on mobile
- Footer stacks vertically (logo, then social icons, then app badges)
- The "Hide on" pattern ensures desktop-optimized blocks are replaced
  with mobile-optimized versions — not just reflowed
- Social icon rows: desktop has horizontal layout (logo + icons in
  one row), mobile has stacked layout (logo above, icons below)

### 11.8 Banner Co-Branding Lockup & Layout

> Extracted from Figma banner screenshots showing HC and TH banners
> with partner logos (teikametrics, WeWork), including correct sizing,
> a documented sizing fuckup, and element positioning.

**Banner dimensions (confirmed):**
- Desktop: **944 × 422px**
- Mobile: 514 × 828px (stacked variant, see Section 2.3)

**Two-zone layout:**

```
┌──────────────────────────┬───────────────────────────┐
│                          │                           │
│   Co-branding lockup     │     Phone mockup          │
│   (plum | partner)       │     showing app screen    │
│                          │                           │
│   "Hey There!"           │     (+ illustration       │
│       ✦                  │      if applicable)       │
│   Subtitle/value prop    │                           │
│                          │                           │
└──────────────────────────┴───────────────────────────┘
     Left half (~45%)            Right half (~55%)
```

- **Left half**: text content zone — co-branding lockup at top, greeting,
  decorative sparkle, subtitle
- **Right half**: visual zone — phone mockup showing the relevant app
  screen (Health Checkup Report, TeleHealth card), sometimes with an
  illustrated character (doctor)
- **Background**: pink gradient (left) → mint/teal gradient (right),
  with particle/dot texture at the transition

**Co-branding lockup structure:**

```
  plum  │  partnerlogo
```

- Plum wordmark (coral/red) + thin vertical divider + partner logo
- Divider is a light/subtle line, ~1px, slightly shorter than logo height
- Positioned at the top of the left zone, centered horizontally within it
- If the partner's org also has standalone branding, it appears
  **independently above** the lockup (see WeWork example: large "wework"
  at top, then the "plum | wework" lockup below it)

**Logo sizing — the critical rule:**

| Partner logo size | Status | Why |
|-------------------|--------|-----|
| ~104 × 27px | CORRECT | Visually proportional to the Plum wordmark — neither dominates |
| ~208 × 54px | WRONG | 2× the correct size. Partner logo visually overwhelms Plum's wordmark, breaking brand hierarchy |

**The rule:** The partner logo must be **visually equal to or slightly
smaller** than the Plum wordmark. Plum sets the sizing baseline. When in
doubt, scale the partner logo DOWN until it feels balanced — never up.
The co-branding lockup should read as "Plum + Partner", not
"partner (and also plum)".

**Text positioning within left zone:**

| Element | Style | Position |
|---------|-------|----------|
| Co-branding lockup | Logo images | Top of left zone, horizontally centered |
| Greeting | Large serif (GT Alpina), dark plum | Below lockup, ~24px gap |
| Decorative sparkle | Small star/sparkle icon, muted | Below greeting, centered under text |
| Subtitle / value prop | Medium serif, dark plum, 2–3 lines max | Below sparkle, ~16px gap |

**Greeting text varies by email type:**
- "Hey There!" — general (HC, TH activation)
- "Welcome!" — onboarding / enrollment
- Never personalized in the banner (personalization happens in body text below)

**Subtitle examples:**
- "Your Comprehensive Health Checkup is ready to book"
- "Personalised care from a doctor is just a call away"
- "Enroll to access your insurance benefits"

**Right zone — phone mockup rules:**
- Phone frame uses a realistic iOS chrome (status bar: 9:00, signal, wifi, battery)
- Screen content matches the campaign's product (HC report with biomarker
  gauge, TeleHealth card with description)
- If an illustrated character is used (e.g. doctor), it sits below/beside
  the phone, slightly overlapping, inside a circular mask in Figma
- The phone mockup is slightly rotated or angled for visual interest
- Mockup extends to the right edge of the banner (can bleed off-edge)

**Common banner mistakes (from screenshots):**

1. **Partner logo too large** — at 208×54 the teikametrics logo dominated
   the lockup. The correct size was 104×27. Always check that the
   partner logo doesn't visually outweigh Plum's wordmark.

2. **Text misalignment** — greeting and subtitle should be left-aligned
   within the left zone, centered as a group. Don't center each line
   independently (creates a ragged mess).

3. **Wrong aspect ratio for phone mockup** — the mockup should show a
   real app screen at phone proportions, not a stretched or cropped
   screenshot.

4. **Missing co-branding divider** — the thin vertical line between
   logos is subtle but structurally important. Without it, the two
   logos look accidentally adjacent.

### 11.9 Anti-Patterns (What Plum Does NOT Do)

- **No dark backgrounds** for body content — always white
- **No multiple competing CTAs** in the body — one primary per email
- **No centered body text** — always left-aligned
- **No all-caps body text** (only in banner headlines baked into images)
- **No animated GIFs** in production emails (editor supports them, Plum
  doesn't use them)
- **No pure black text** — always the warm plum/maroon
- **No pill-shaped buttons** (border-radius: 50%) — moderate radius (8px)
- **No background colors on text sections** — no colored callout boxes
- **No more than one font** in body copy (serif is reserved for
  display-level headlines in images)

---

> **Sources**: Plum's actual CleverTap email editor (screenshots from Aug 2026),
> live Plum email renders (CD Account, Day 2 Onboarding, Data Labs Heart Disease),
> CleverTap product docs, EMAIL-DESIGN-PLAYBOOK.md, Copy_SKILL.md.
> Last updated: 21 August 2026.
