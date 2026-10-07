# Plum Email Collateral — Build Playbook

Everything needed to generate Plum email header/footer/CTA PNGs from the Figma
templates and hand them to CleverTap. Combines the original brief with
everything learned actually doing it.

Design system for Plum campaign email collateral

---

# PART 1 — READ THIS FIRST (the traps)

These cost the most time. Read before touching anything.

### 1.1 The Figma file MUST live in a paid team

The Figma MCP rate limit is enforced **per the file's owning team plan**, not
per user.

| File location | MCP |
|---|---|
| `Plum product` team (paid) | works |
| A Free-plan team | `You've reached the Figma MCP tool call limit on the Starter plan` |

Verified by testing two files with the same account. A file in a Free team is
unusable no matter how many times you retry. Keep the working file in
**Plum product** (Drafts inside it is fine).

### 1.2 Brand fonts are not in Figma by default — and installing them is not enough

Templates reference these; Figma ships **none** of them:

| Font | Used for | Where the file is |
|---|---|---|
| GT Alpina Medium | headlines | `Grilli Type Order 121528/GT Alpina/GT-Alpina-Standard-Medium.otf` |
| GT Alpina Bold | numerals in mocks | same folder |
| GT Alpina Regular | mobile subtext | same folder |
| Passenger Sans Semibold | button labels | `ITF-Order-20250121/Fonts/Passenger Sans/OTF/` |
| Passenger Sans Regular / Medium | mock body text | same folder |
| Passenger Sans **Bold** | mock numerals | **NOT IN THE ORDER — needs purchasing** |
| Inter (all weights) | body copy | already in Figma |

**Installing the fonts is step 1 of 2.** Figma caches its font list at launch,
so after installing you MUST **quit Figma completely (⌘Q) and reopen**. Then
open the file in the **desktop app** — the local font agent
(`figma_agent --from-desktop-app`) serves the desktop app, not a browser tab.

Verify with:
```js
const all = await figma.listAvailableFontsAsync();
return all.map(f => `${f.fontName.family}/${f.fontName.style}`)
          .filter(s => /alpina|passenger/i.test(s));
```
Empty array = not visible yet. Do not proceed expecting accurate type.

**Also:** Trial files leak into `~/Library/Fonts`
(`GT-Alpina-Condensed-Bold-Trial.otf` etc). Delete them so nobody ships work
set in a trial licence. One template text node still references
`GT Alpina Trial / Regular` — worth fixing at source.

### 1.3 Fallback font when GT Alpina is unavailable: Vollkorn

**Do not fall back to Inter.** GT Alpina is a serif; Inter is a sans, so the
design reads as a different brand entirely.

**Vollkorn** is in Figma (12 weights) and is a serif, so it preserves the
design's character. Map `GT Alpina Medium → Vollkorn Medium`,
`GT Alpina Regular → Vollkorn Regular`. Label any such output clearly —
it is a stand-in, not a match, and must never ship.

Other serifs available if Vollkorn is ever wrong: Spectral, Source Serif 4,
Newsreader, Literata, Lora, Crimson Pro, EB Garamond, Petrona, Fraunces.

### 1.4 Figma refuses to reparent subtrees containing unloaded fonts

`appendChild` throws — not just text edits:

```
Error: in appendChild: unloaded font "Passenger Sans Semibold".
```

**Working order — do not deviate:**

1. `figma.loadFontAsync` every font you intend to *use*
2. `src.clone()` (this succeeds even with missing fonts)
3. Walk the clone's TEXT nodes and reassign `fontName` to an available font
4. **Then** `figma.currentPage.appendChild(clone)`
5. Then position, rename, edit copy

Scripts are **atomic** — a failure changes nothing, so a failed attempt is
safe to fix and retry.

In this file `clone()` lands the copy at **page level** (`parent = 0:1`), not
inside the source frame — so originals stay untouched. Verify per file.

### 1.5 Images added via the API NEVER appear in exported PNGs

The single biggest trap. `figma.createImage()` produces a valid image
(confirmed: correct hash, right byte length, valid PNG header, renders
perfectly on the live Figma canvas) — but Figma's **server-side renderer**,
which produces `get_screenshot` / `node.screenshot()` output, never receives
it. Waiting does not help.

Proof: pixel-scan the logo region of an export and count brand-coloured
pixels — result is `0` while the logo is plainly visible in the editor.

**Therefore the client logo must be composited locally at export time.**
This is a required pipeline step by design. See §5.4.

### 1.6 Other API/tool limits worth knowing

| Limit | Detail | Work-around |
|---|---|---|
| `get_screenshot` never upscales | `maxDimension` caps only; a 944px node returns 944px | Fine at 1x (our spec). For 2x use `exportAsync` |
| `get_metadata` on large nodes | fails with `Invalid JSON: EOF while parsing` | Scope to a child node, or use `use_figma` returning a trimmed tree |
| `run_dataset` | max 500 rows | filter/aggregate |
| `export_dataset` | max 2000 rows, sets `truncated=true` | ask for an aggregated slice |
| Banned APIs in `use_figma` | `createImageAsync`, `loadAllPagesAsync`, `setPluginData`, `figma.notify()` | use `figma.createImage(bytes)`; `return` for output |
| Page switching | `figma.currentPage = p` throws | `await figma.setCurrentPageAsync(p)` |

---

# PART 2 — SOURCE FILES

| What | File key | Notes |
|---|---|---|
| Email templates | `3J4g2wdTGz5IGrb9tjECGt` (Figma Training Doc) | in Plum product → Drafts |
| Colour system + illustrations | `bw1UDCiKdbwR7MLFqUPbdv` (Daydream Illustrations) | published library, read-only |

Daydream holds 14 named colour ramps (steps 50→500): Reds, Roses, Apples,
Grapes, Vision, Lavender, Blues, Teals, Guavas, Lemons, Mangoes, Oranges,
Beige, Greys.

---

# PART 3 — TEMPLATE INVENTORY

All node IDs as of 2026-08-21. **Re-verify after any template reorganisation** —
these shifted once already when Adoption Emails Headers was merged into
Welcome.

### 3.1 Header variants — four, pick one

| Variant | Node | Size | Use |
|---|---|---|---|
| Desktop, single brand | `1:197` "Email banner single brand" | 944 × 422 | Plum-only emails |
| Desktop, co-branded | `23:220` "Email header cobranded" | 944 × 422 | client emails |
| Mobile, single brand | `23:678` "Mobile single" | 514 × 828 | Plum-only |
| Mobile, co-branded | `1:896` "Mobile cobranded" | 514 × 828 | client emails |

**The AM chooses single vs co-branded.** Every email needs both a desktop and
a mobile export.

### 3.1b HRA adoption headers

| Variant | Node | Size |
|---|---|---|
| Desktop | `160:620` "HRA Desktop" | 1023 × 507 |
| Mobile | `160:638` "HRA Mobile" | 514 × 721 |

**Single brand, no partner logo slot** — HRA is a Plum product campaign, not
a client co-branded one. This is the documented exception to §7's client-logo
rule, and §7 states it too. Template copy is already correct: heading "Meet your
Health Risk Assessment" (42px), subtext "Answer a few questions / and
personalise your health journey." (20.55px, break already set). Only the font
substitution is needed. See `CREW-M-CAMPAIGN-PLAYBOOK.md` §5.

### 3.2 Footers — pick one pair

| Node | Size |
|---|---|
| `104:445` "Footer desktop" | 597 × 295 |
| `104:408` "Footer mobile" | 376 × 186 |

Both live inside `1:730` "All Email Footers".

> **Updated 2026-08-21.** These replace the earlier `1:738` (600 × 325) and
> `1:784` (376 × 214). The new artwork drops the social icons and the baked-in
> unsubscribe line, so **unsubscribe must now be live HTML text below the
> footer image**, not part of it. Dimensions changed too — do not reuse the old
> sizes. Re-verify node IDs each session; these moved once already.

Contents of the current artwork: a "Download the Plum app" block with QR code
over a soft pink illustrated band, then a dark plum bar (`#571541`-family)
carrying the Plum wordmark. No social icons and no unsubscribe line.

**Footers are fixed artwork — never recoloured.** They do not follow any accent.

### 3.3 CTA button

`1:726` "Button" inside `1:718` "All Email Buttons" — 184 × 34, fill
`#571541`, children: chevron / `Label` TEXT / chevron.

Rules:
- Label is **4–5 words** (the placeholder literally reads "Button CTA in 4-5 words")
- **Never change the button colour** unless explicitly asked
- Frame auto-hugs: a 4-word label grows it 184 → ~223px. Do not resize manually
- Sits toward the **end of the body**, below the copy
- The co-branded desktop header has **no** button — take it from this frame

### 3.4 Illustrations

`1:840` "Illustrations" — eight, already named by topic, so they self-map:
Health Insurance · Personal Accident Insurance · Term Life Insurance ·
Plum Telehealth · Mental Health · Cultpass benefits · Health Checkup ·
In App Support

### 3.5 The eight `02_doc` colour modules

217 × 192, corner radius 17.55, **radial gradient** from `#FAF6F0` to an accent:

| Node | Accent | Reads as |
|---|---|---|
| `1:1078` | `#6BD7EC` | blue / cyan |
| `1:1082` | `#73D5AF` | mint |
| `1:1084` | `#B0D365` | lime |
| `1:1086` | `#FDAAE6` | pink / magenta |
| `1:1080` | `#F89472` | coral |
| `1:1093` | `#FF9FA8` | salmon |
| `1:1091` | `#FFD46B` | yellow |
| `1:1088` | `#CAAFF6` | lavender |

The mobile header's coloured band **is** an `02_doc` module.

### 3.6 The six "(Recommended) Colours" swatches

Solid tints, and their Daydream tokens:

| Hex | Token |
|---|---|
| `#FED5F2` | Rose/150 |
| `#FFBFC5` | Red/150 |
| `#E5D7FA` | Lavender/150 |
| `#96DFC3` | Teal/**200** |
| `#D8E9B2` | Guava/150 |
| `#FCC9B9` | Orange/150 |

Note Teal is step **200** while the rest are 150 — unexplained, possibly a
slip. Also this row omits blue and yellow, which the module set has. **Treat
the eight modules as the source of truth.**

---

# PART 4 — DESIGN RULES

### 4.1 Email structure (fixed)

```
Header image  (desktop + mobile variants)
Text
Button
Footer
```

### 4.2 Locked — never change

- **Layout.** Position of text, subtext, image, background placeholder.
- **Button colour** (`#571541`), unless explicitly asked.
- **Footer artwork.**

### 4.3 Changes per email

- Header **title and subheading**, so the header reads in sync with the body.
  Never leave placeholder copy ("Heading that fits in 2 lines").
- Button label (4–5 words).
- Client logo in the co-branding slot.

### 4.4 Colour — FIXED, brand-independent

**Current rule:** every client gets the **same** header colour. Do **not**
derive it from the client's logo.

The approved treatment (the accepted reference build):
- background gradient final stop → `#FFBFC5`
- the large decorative ellipse → `#FFBFC5`

> Historical note: an earlier rule matched the accent to the client's brand
> colour by hue distance. It was built and works — logo → dominant colour →
> nearest of the eight modules — but was **dropped** in favour of
> consistency. Don't reintroduce it without asking. If it's ever revived,
> note that two-colour brands 
> need a tie-break — take the tightest hue match.

Where the accent lives:

| Variant | Gradient node | Ellipse |
|---|---|---|
| Desktop | `Rectangle 3` (VECTOR), last gradient stop | largest ELLIPSE (~697px) |
| Mobile | the `02_doc` frame, last gradient stop | largest ELLIPSE |

Ellipse names differ between variants (`Ellipse 2773`, `Ellipse 2774`,
`Ellipse 2772`) — **select by size, not name**:
```js
const ell = root.findAll(n => n.type === 'ELLIPSE')
                .sort((a,b) => b.width - a.width)[0];
```

### 4.5 Which creative goes in the phone mock

**Use the Health Score screen. Not the Health Report screen.**

The co-branded desktop template ships with a "Package / Report" mock (Health
Report, 303 × 932). Replace it with the health-score phone from the
single-brand template:

- source: `1:197` → `GP / List of doc / free` (`1:203`, 272 × 589 at x 587, y 83)
- both frames are 944 × 422, so **reuse the source x/y verbatim** and it lands correctly
- then `.remove()` the Package / Report frame

The phone mock is a flat raster screenshot — it is always pink and cannot be
recoloured. (Irrelevant now colour is fixed, but it constrained the earlier
colour-matching rule.)

---

# PART 5 — TYPOGRAPHY

### 5.1 Fonts

| Role | Font | Class |
|---|---|---|
| Headlines | **GT Alpina** | serif |
| Body | **Inter** | sans |
| Occasional | Times New Roman | serif |

Fallback stacks — **split by class, never one stack for both**:
```css
/* headings: GT Alpina is a serif, so Times New Roman is a correct fallback */
font-family: "GT Alpina", "Times New Roman", Georgia, serif;

/* body: Inter is a sans — must NOT fall back to Times New Roman */
font-family: Inter, Helvetica, Arial, sans-serif;
```

The Figma text style `Typography/Family/Serif` = GT Alpina. Its reference is
currently **broken** in the file.

### 5.2 Baked into PNG vs live HTML text

Verified against a production email (a reference production email) by checking
which strings existed in the PDF's text layer:

| Element | Rendering |
|---|---|
| Header headline + subheading | **baked into the PNG** |
| Logo lockup | baked |
| Body copy, bullets | **live HTML text** |
| Section headings | **live HTML text** |
| Illustration cards, button, footer | images |

Consequences:
- Header type can be any font — it's pixels by send time.
- **GT Alpina will never load in email** (licensed Grilli Type face, not on
  Google Fonts; Gmail strips web fonts, Outlook desktop never loads them). So
  any GT Alpina heading left as live text renders as Times New Roman for
  nearly everyone. If it must look like GT Alpina, **bake it into the image.**
- Production body copy is **plum/purple, not black**.

### 5.3 Exact type specs (measured)

**Desktop — single brand (the accepted reference):**

| Element | Value |
|---|---|
| Heading | GT Alpina Medium, **40px**, letterSpacing −2%, lineHeight AUTO, CENTER |
| Subtext | 18px, lineHeight 120%, letterSpacing −2%, CENTER |
| Container | VERTICAL auto-layout, itemSpacing 16, counterAlign CENTER |
| Button label | Passenger Sans Semibold, 14px, lineHeight 18px |

**Desktop — co-branded (the cobranded variant):**

| Element | Value |
|---|---|
| Heading | 45px, letterSpacing −2%, CENTER |
| Subheading | **18px** ← template ships 30px, which is too big. Always reduce to 18 |
| Container | VERTICAL, itemSpacing 30 (outer) / 2 (inner) |

**Mobile — both variants:**

| Element | Value |
|---|---|
| Heading | 49.59px, letterSpacing −2%, CENTER |
| Subtext | 20.55px, lineHeight 120%, CENTER |
| Container | VERTICAL, itemSpacing 24 (outer) / 16 (inner) |

Mobile ships correct — don't touch it. **Only the desktop co-branded
subheading needs fixing (30 → 18px).**

> **Use these numbers, do not invent your own.** The current family templates
> are mobile heading 49.59 / subtext 20.55, desktop heading 40 / subtext 18.
> When a headline looks oversized next to its subtext, the cause is usually
> that the subtext was never set at all and kept a stale default — not that
> the heading needs shrinking. Shrinking both throws the whole scale off.

### ⚠️ Heading length is limited by geometry, not taste

The heading node is **fixed-width** with `textAutoResize = 'HEIGHT'` (394px
desktop, 429px mobile). Longer copy cannot widen it, so it wraps and the node
grows **taller**. That node sits in a vertical auto-layout, so its growth
pushes the divider and subheading down — and the parent frame is 944 × 422
with `clipsContent: true`, so anything past the bottom edge is silently cut
off. The symptom looks like "the creative is distorted"; the cause is a
clipped subheading.

It behaves as a cliff, not a gradient. Measured with
"Your health and wellness benefits for 2026-27":

| Heading size | Node height | Lines |
|---|---|---|
| 45px (template default) | 168 | 4 |
| 40px | 168 | 4 |
| 37px | 156 | 4 |
| **34px** | **94** | **2** |

At 37px "wellness" no longer fits line one, forcing four lines; at 34px it
fits and collapses to two.

**Rules:**
- Keep the heading node **≤ ~100px tall** (two lines).
- 45px holds roughly 20 characters per line. Longer headings need a smaller size.
- **Assert the height in code after setting copy** — don't eyeball it:
  ```js
  h.characters = HEADING;
  if (h.height > 100) throw new Error('heading wraps past 2 lines: ' + h.height);
  ```
- Either shorten the copy or drop the size. Never let it run to 3+ lines.

---

# PART 6 — THE CO-BRANDING LOCKUP

### 6.1 Figma node structure

Structure in the co-branded variants:

```
Group 1000004438
├── Logo Co branding Unit  (FRAME 238×27, clipsContent false)
│   ├── Logo               (Plum wordmark, 64.8 × 20.7)
│   └── <client logo>      (RECTANGLE 95 × 27, IMAGE fill)
└── Line 1                 (LINE, the divider)
```

The client slot ships with **Acentra Health's** logo as placeholder, named
`Press_Release_Logo_Acentra_Health_RGB_...`. Rename it when you replace it.

**Slot is 95 × 27 — sized for a wordmark.** A square icon mark must either be
resized to 27 × 27 (safe, no layout change) or the aspect will distort.
Always prefer the client's **wordmark**.

Slot position relative to the frame, for local compositing:

| Variant | Slot x, y | Size | Plum logo x, y |
|---|---|---|---|
| Desktop `26:203` | 225.4, 87.5 | 27 × 27 | 116, 90.6 |
| Mobile `26:660` | 276.9, 73.6 | 27 × 27 | 167.5, 76.7 |

Re-measure per build with `absoluteBoundingBox` deltas — do not assume.

### 6.2 Banner two-zone layout

The desktop banner (944 × 422) is split into two zones:

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

- **Left half (~45%)**: text content — co-branding lockup at top, greeting,
  decorative sparkle, subtitle.
- **Right half (~55%)**: visual — phone mockup showing the relevant app
  screen (HC report with biomarker gauge, TeleHealth card), sometimes with
  an illustrated character (doctor in circular mask).
- **Background**: pink gradient (left) → mint/teal gradient (right),
  with particle/dot texture at the transition zone.

### 6.3 Logo sizing — the critical rule

| Partner logo size | Status | Why |
|---|---|---|
| ~104 × 27px | **CORRECT** | Visually proportional to the Plum wordmark — neither dominates |
| ~208 × 54px | **WRONG** | 2× the correct size. Partner logo overwhelms Plum's wordmark, breaks brand hierarchy |

**The rule:** The partner logo must be **visually equal to or slightly smaller**
than the Plum wordmark. Plum sets the sizing baseline. When in doubt, scale the
partner logo DOWN until it feels balanced — never up. The lockup should read as
"Plum + Partner", not "partner (and also plum)".

The lockup structure is:

```
  plum  │  partnerlogo
```

- Plum wordmark (coral/red) + thin vertical divider (~1px, slightly shorter
  than logo height) + partner logo
- Positioned at the top of the left zone, horizontally centered within it
- If the partner org has standalone branding, it can appear **independently
  above** the lockup (see WeWork: large "wework" at top, then "plum | wework"
  lockup below it)

### 6.4 Text positioning within the left zone

| Element | Style | Position |
|---|---|---|
| Co-branding lockup | Logo images | Top of left zone, horizontally centered |
| Greeting | Large serif (GT Alpina), dark plum | Below lockup, ~24px gap |
| Decorative sparkle | Small star/sparkle icon, muted | Below greeting, centered |
| Subtitle / value prop | Medium serif, dark plum, 2–3 lines max | Below sparkle, ~16px gap |

**Greeting text varies by email type:**
- "Hey There!" — general (HC, TH activation)
- "Welcome!" / "Welcome back!" — onboarding / enrollment / renewal
- Never personalized in the banner (personalization happens in body text)

**Subtitle examples:**
- "Your Comprehensive Health Checkup is ready to book"
- "Personalised care from a doctor is just a call away"
- "Enroll to access your insurance benefits"

### 6.5 Phone mockup rules (right zone)

- Phone frame uses realistic iOS chrome (status bar: 9:00, signal, wifi, battery)
- Screen content matches the campaign's product (HC report with biomarker
  gauge, TeleHealth card with consultation description)
- If an illustrated character is used (e.g. doctor), it sits below/beside
  the phone, slightly overlapping, inside a circular mask
- The phone mockup is slightly rotated or angled for visual interest
- Mockup can extend to the right edge of the banner (bleed off-edge is fine)

### 6.6 Common banner mistakes

1. **Partner logo too large** — at 208×54 the teikametrics logo dominated
   the lockup. Correct was 104×27. Always check that the partner logo
   doesn't visually outweigh Plum's wordmark.

2. **Text misalignment** — greeting and subtitle should be left-aligned
   within the left zone, centered as a group. Don't center each line
   independently (creates a ragged mess).

3. **Wrong aspect ratio for phone mockup** — the mockup should show a
   real app screen at phone proportions, not a stretched or cropped screenshot.

4. **Missing co-branding divider** — the thin vertical line between logos
   is subtle but structurally important. Without it, the two logos look
   accidentally adjacent.

---

# PART 7 — THE CLIENT LOGO

## RULE: every client header carries the client logo

**Updated 2026-08-22, and this supersedes the earlier "ask the AM, never
scrape" rule below.** A header showing only the Plum wordmark must never
ship. Resolve the logo in this order:

1. The file the AM uploaded in the `/crew-m` Slack modal.
2. If none was uploaded, **search the internet for it using the account name,
   download it, and use it.**
3. Only if both fail, stop and ask — do not send without it.

Treat a missing client logo as a blocking defect, the same as a leftover
placeholder string. The failure modes in the table below are real and still
worth knowing (they are why step 1 is preferred), but they are no longer a
reason to ship without a logo — they are a reason to check the one you found
before using it: right company, dark-on-light, wordmark over icon, not a
favicon-sized crop.

### The one exception: Plum product campaigns

This rule governs **client** emails — welcome, renewal, anything addressed to
one organisation's employees on behalf of that organisation. It does not
govern **Plum product campaigns**, which go to members across every account
and have no single client to co-brand with. Those templates ship single-brand
with no partner logo slot at all, so there is nothing to fill.

Currently that means the **HRA adoption** headers (§3.1b, Figma `160:620` and
`160:638`).

**The test:** if a template contains a `Logo Co branding Unit`, the rule
applies and the client logo is mandatory. If it contains none, the design is
single-brand on purpose — do not graft a lockup onto it to satisfy the rule.

### Historical note — why scraping was originally rejected

This replaces an earlier approach of fetching the logo from the client's
website. That was tried properly and is not reliable enough for client-facing
email. What went wrong, so nobody re-litigates it:

| Problem | Evidence |
|---|---|
| Name to domain guessing fails silently into the **wrong company's** logo | Guesses based on client name resolve to unrelated companies or 404 |
| Clearbit's logo API is dead | HTTP 000, retired post-HubSpot |
| Public logo sources are unreliable | Favicon services, scraped sites and public brand pages return wrong sizes, wrong colour variants, or 403 to automated requests. Source logos from a reviewed asset store, not the web. |

So: ask the AM. It is one attachment and it removes every failure above.

**Spec to request:** PNG or SVG, transparent background, **dark-on-light**
variant (the header is cream), wordmark rather than icon-only where possible.
The slot is natively 95 × 27.

If the client's mark is square rather than a wordmark, resize the slot to
27 × 27 — that preserves aspect without altering the template layout.

**The AM still approves the final creative before send.**

Sampling brand colour is no longer needed (accent is fixed, §4.4), but if it
ever is: sample the *app icon*, not the wordmark SVG. Plum's wordmark SVG is
`#FFFAF2` (the white-on-dark version) while the real brand red `#FC3C48`
only shows in the icon.

---

# PART 8 — BUILD PROCEDURE

### 8.1 Inputs from the AM

1. **Client name**
2. **Single or co-branded**
3. **Client logo file** — required if co-branded (§7). PNG/SVG, transparent,
   dark-on-light, wordmark preferred.
4. **New client or renewal** — changes the copy framing
5. **Benefit specifics not in the warehouse** — ambulance cap, LASIK, Ayush,
   family-definition wording. Omit rather than invent if not supplied.

Everything else is derived: insurer, TPA, sum insured, coverage dates,
maternity limits, coverage type all come from `policy_schedule` /
`iw_policy_si`. (changes the copy: "Welcome!" vs "Welcome back!")

### 8.2 Steps

**1. Verify environment**
- File is in Plum product
- `listAvailableFontsAsync` shows GT Alpina + Passenger Sans (else use Vollkorn and label it)

**2. Inspect the file fresh.** Node IDs move. Dump page-level children and
re-locate the four header variants, footers, buttons.

**3. Pull policy data** (see Part 9) for real dates. Never invent them.

**4. Clone the chosen header variants** (desktop + mobile) —
load fonts → clone → swap fonts → appendChild → position → rename.

Naming convention: `GEN — <EmailType> — <Client> — <desktop|mobile> <variant>`
plus a `[FONTS SUBSTITUTED]` / `[VOLLKORN sub for GT Alpina]` suffix whenever
the type isn't real. Place at **x ≥ 19000** to stay clear of the templates.

**Never modify the originals or their names.**

**5. Set copy.** Heading 2 lines, subheading 2 lines, CTA 4–5 words.

**6. Fix the desktop subheading to 18px.**

**7. Swap the creative** to the Health Score phone (§4.5).

**8. Apply the fixed accent** `#FFBFC5` (§4.4).

**9. Replace the client logo** in the co-branding slot. It will look right in
Figma and be **absent from exports** — expected; §8.3 handles it.

**10. Clone footer + CTA button**, set the label.

**11. Export at 1x** and composite the logo locally.

### 8.3 Export + local logo composite

Export sizes (1x, native — **no @2x**):

| Asset | Size |
|---|---|
| Header desktop | 944 × 422 |
| Header mobile | 514 × 828 |
| Footer desktop | 600 × 325 |
| Footer mobile | 376 × 214 |
| CTA button | hugs (~223 × 34) |

Then composite:
```python
from PIL import Image
logo = Image.open('client-logo.png').convert('RGBA')
for f, x, y, w, h in [
    ('header-desktop.png', 225.4, 87.5, 27, 27),
    ('header-mobile.png',  276.9, 73.6, 27, 27),
]:
    base = Image.open(f).convert('RGBA')
    base.alpha_composite(logo.resize((int(w), int(h)), Image.LANCZOS),
                         (int(round(x)), int(round(y))))
    base.convert('RGB').save(f.replace('.png', '-logo.png'), 'PNG')
```

### ⚠️ Measure the slot LAST, and verify the pixels

Two failures, both hit for real:

**1. Stale coordinates.** The logo sits inside a **vertical auto-layout**. Any
change to heading size or copy length reflows that stack and *moves the logo
row*. Measuring the slot before a text change and compositing after puts the
logo in the wrong place. Observed: changing the mobile heading 49.6 → 34px
moved the slot from y 39.1 to **y 95.6**, a 56px error. Desktop was unaffected
by the same edit, so checking one and assuming the other is not safe.

> **Rule: re-measure `absoluteBoundingBox` immediately before compositing,
> after every layout or copy change. Never reuse a coordinate across edits.
> Measure desktop and mobile separately.**

**2. Silent misses.** A composite at the wrong offset produces a valid-looking
PNG with the logo in dead space. Always assert the pixels, per variant:

```python
def verify(path, x, y, w, h):
    crop = Image.open(path).convert('RGB').crop((int(x)-3, int(y)-3, int(x+w)+3, int(y+h)+3))
    brand = dark = 0
    for (r, g, b) in crop.getdata():
        if <brand-hue test>: brand += 1
        if r < 70 and g < 70 and b < 70: dark += 1   # wordmark
    assert brand > 20 and dark > 50, f'logo missing in {path}'
```

Never hand over an export whose logo hasn't been asserted in pixels.

---

# PART 9 — DATA SOURCES

Most of a welcome email is per-org policy data, reachable through the
`insurwreck-data` MCP server.

| Email field | Dataset · column |
|---|---|
| Client / org name | `account_health.org`, `iw_policy_si.org_name` |
| Insurer | `iw_policy_si.insurer` |
| TPA | `policy_schedule.tpa` |
| Sum insured | `policy_schedule.grade_sum_insured` |
| Coverage start | `policy_schedule.inception_date` |
| Renewal / expiry | `policy_schedule.expiration_date` |
| Maternity limits | `policy_schedule.maternity_limit_normal` / `_caesarean` |
| Coverage type (ESC/ESCP) | `policy_schedule.coverage_type` |
| Segment | `account_health.segment` |

Dataset IDs: `policy_schedule` 19251 · `iw_policy_si` 19648 ·
`account_health` 19244 · `iw_claims_base` 19638

**Not in the warehouse** — must be supplied: ambulance cap, LASIK, Ayush,
family-definition wording, helpline copy.

Constants: helpline `1800 30 911 911`, support `care@plumhq.com`,
sender `updates@info.plumhq.com`.

**Caveats learned:**
- Every export is **capped at 2000 rows** and returns `truncated=true`. A
  missing org may simply be beyond the cap.
- Plum's own current policy was **not findable** — only test orgs ("Plum
  Test", "Plum OPD only Org", "Plum Partner Program") plus an expired
  2023–24 `Plum Benefits Private Limited` GMC.
- A typical account resolves fine: name, segment, policy ID all present
  `OG-26-9906-8403-00000493`, TPA in-house, 7 Dec 2025 → 6 Dec 2026.
- `currentAccountManagerEmail` comes back masked (`…@masked.invalid`).
- **Never invent a date for a real client.** Derive it and say it's derived.

---

# PART 10 — PRODUCTION EMAIL STRUCTURE (reference)

Observed in a real welcome email, for copy/section order:

1. Header image (co-branded, "Welcome back!" + one-line subheading)
2. Intro — partnership, client name bold
3. Insurer paragraph
4. "Here's when it starts:" — coverage start date
5. "Here's what you need to know:" — bullets (health cards, helpline, cashless vs reimbursement)
6. "Note:" — claims before the new policy date
7. "Next steps:" — enrollment invite
8. "Here's what you're covered for" — illustration card + policy summary
9. "Health Insurance Benefits for \<year\>" — limits as bullets
10. "Reaching out to Plum" — illustration card + support channels
11. Footer

Subject-line convention: `<Subject> 🎉 <Client> <> Plum`

Note the production email has **no CTA button**; the template requires one.
Moving to the template therefore adds a button — confirm the copy with whoever
owns messaging.

---

# PART 11 — OPEN ITEMS

- [ ] GT Alpina + Passenger Sans visible to Figma (install done; **restart pending**)
- [ ] Purchase **Passenger Sans Bold** — not in the ITF order
- [ ] Delete Trial GT Alpina files from `~/Library/Fonts`
- [ ] Fix the broken `Typography/Family/Serif` style reference
- [ ] Fix the stray `GT Alpina Trial / Regular` node in the template
- [ ] Confirm: is Teal/**200** in the recommended row intentional?
- [ ] Confirm: are live serif section headings meant to render as Times New Roman?
- [ ] Source client **wordmarks** (not icons) — or define an icon-only lockup rule
- [ ] Decide CTA copy for welcome emails (with Kritin)
- [ ] Companion guides: CleverTap (Vishrut), Copy (Kritin)
