# FlywheelCAD — Python Scripting Guide for Coding Agents

This is a task-oriented reference for an LLM/coding agent authoring a FlywheelCAD
design **in Python**. It covers the mental model, the full API surface, the rules
that are easy to get wrong, and complete worked examples.


The authoritative API is `FlyWheelCADV3/Resources/flywheelcad.py`. Runnable
example scripts live in `TestProjects/` (indexed in `TestProjects/EXAMPLES.md`)
and `Samples/`. When in doubt, read those.



## Contents

This file is the entry point. It carries everything needed to write a correct
script: the deliverable format, the API index, the rules, and the 2D → region →
3D path. Reference material that is only needed for a particular job lives in
`docs/` and is listed below — **read those on demand, not up front.**

**In this file**

- **[A. What to deliver: a `.fwcad` project bundle](#a-what-to-deliver-a-fwcad-project-bundle)** — the output format, and why it beats a bare `.py`
- **[B. API index](#b-api-index)** — every public call, one line each: signature, what it returns, what it raises
- [1. The model in 60 seconds](#1-the-model-in-60-seconds) · [2. File skeleton](#2-file-skeleton) · [3. Rules an agent MUST follow](#3-rules-an-agent-must-follow)
- [4. Sketching (2D)](#4-sketching-2d) · [5. Regions](#5-regions--the-bridge-from-2d-to-3d) · [6. Bodies (3D)](#6-bodies-3d)
- [9. Quality & performance knobs](#9-quality--performance-knobs) · [10. Pitfalls checklist](#10-pitfalls-checklist-for-generated-scripts) · [12. Where to look next](#12-where-to-look-next)

**This is the complete single-file edition.** In the FlywheelCAD repository the guide is split — the entry file plus its `docs/ai-guide-*.md` chapter files read on demand — so a tool loads only the section it needs. Here every section is inline, in order. Section numbers are the same in both, so a reference to §7 means the same section either way.

- [C. Settings that belong to the app, not to your script](#c-settings-that-belong-to-the-app-not-to-your-script) · [D. Author for the UI: real sketches, honest dimensions](#d-author-for-the-ui-real-sketches-honest-dimensions) · [7. Appearance, quality & visibility](#7-appearance-quality--visibility)
- [8. Components & assemblies](#8-components--assemblies) · [11. Complete worked examples](#11-complete-worked-examples) · [13. Errors, refusals and older spellings](#13-errors-refusals-and-older-spellings)

If you read only two of the on-demand sections, read **§C** and **§D**.


---


## A. What to deliver: a `.fwcad` project bundle

**Produce a `.fwcad` project bundle, not a bare `.py` file**, unless the user has explicitly asked for a flat script. Both are valid FlywheelCAD documents and the scripting API is identical in each, so this is a packaging question, not an API one — the bundle is the format the app itself defaults to when a user saves a new document. The sharpest edge of the alternative: a flat script's `lib/` sits in the **enclosing folder**, shared with every other flat script there (two can clobber each other's vendored parts), and copying the `.py` alone **silently breaks it** — `lib/` and any sibling modules are left behind. A bundle's `lib/` is private to it and travels as one Finder item.

### The format

A `.fwcad` is a **macOS document package**: an ordinary directory whose name ends in `.fwcad`, which Finder presents as a single document. There is no archive, no compression, no binary container, and no manifest — everything inside is plain UTF-8 Python you can read, diff and edit with any tool.

```
GearboxMount.fwcad/
├── main.py                     # THE script. Always exactly this name.
├── lib/
│   └── standard/
│       └── steppers.py         # vendored library modules (see §8.6)
└── helper.py                   # optional sibling modules you author
```

Two invariants matter and are enforced in code:

- **The inner script is always named `main.py`.** Resolution never depends on the bundle's user-chosen name, so `GearboxMount.fwcad` and `Bracket.fwcad` both contain a `main.py`. A bundle without one fails to open with a "corrupt file" error.
- **Everything is plain Python.** `cd GearboxMount.fwcad` and any editor keeps working; the directory is not opaque.

### The minimum valid bundle

A directory named `<Anything>.fwcad` containing a UTF-8 file named `main.py`. That is the entire requirement — no manifest, plist, version file or required header; a bundle hand-created this way opens and renders, and the headless renderer consumes it directly.

You should nevertheless write the standard preamble as the first lines of `main.py`, because it is what the app writes and what several app features anchor against:

```python
# flywheelcad-format: 1
from flywheelcad import *
cad = FlywheelCAD()

# ... build the design ...
```

The `# flywheelcad-format: 1` stamp is a **forward-compatibility gate only**. It is read at open: a script declaring a version *newer* than the running build supports is refused up front with a message telling the user to update FlywheelCAD. An older stamp — or no stamp at all — runs exactly as it would otherwise, with no gate and no rewrite. So the stamp is not required, but writing it costs one line and makes the document self-describing. The scan that finds it only looks at the **header** (leading blank/`#` lines, stopping at the first line that is neither) — put it first.

### Practical rules when you write one

- **Name modules carefully.** The bundle root goes on `sys.path`, so a sibling module shadows nothing in the stdlib (the directory is appended at the *end* of the path) but these stems are reserved and must not be used for a file in the bundle root: `flywheelcad`, `sitecustomize`, `component_shape`, `component_export_rewrite`, `document_setting_rewrite`, `test` — plus every stdlib module name. A collision emits a warning naming the file.
- **No `__init__.py` anywhere.** `lib/` and `lib/<library>/` are Python 3 implicit namespace packages; adding `__init__.py` is unnecessary and not the shipped layout.
- **A vendored import path is exactly three dotted components** — `from lib.standard.steppers import stepper`. Deeper or shallower paths do not resolve, and cross-library imports are unsupported.
- **The app rewrites `main.py`.** Any GUI edit re-serialises the script through the command logger, so hand-formatting, comment placement and non-canonical spellings inside `main.py` do not survive a GUI operation. Everything *else* in the bundle is preserved untouched across saves.
- **Do not modify files inside a bundle that is currently open in FlywheelCAD** (other than through the app). An out-of-band write races the app's autosave and produces "The document could not be autosaved." `main.py` is the exception: the app watches it and round-trips external edits deliberately.
- **First open prompts for consent.** A FlywheelCAD document *is* an executable Python script, so the app asks before running one whose exact bytes it has not seen approved before. A bundle you generate will open and display, then prompt once before it executes. This is expected — tell the user to expect it rather than trying to suppress it. A file carrying macOS quarantine (downloaded, emailed) prompts on *every* open and is never remembered.

### Converting between the two

The app does this in both directions, so a user is never stuck with the format you chose: **File ▸ Convert to Project Bundle…** turns a saved flat script into a bundle (copying its dependency closure), and **File ▸ Export as Flat Script…** writes a bundle back out as a `.py` plus its dependencies. Inserting a library part into a flat saved document offers the conversion automatically.



---

## B. API index

Every public call, with what it returns and the constraints that are easy to
miss. Sections in the right-hand column point at the prose that explains the
behaviour. `name=` is available on essentially every Ref-producing call (see §3
rule 1) and is omitted from this table except where it is the only way to name
the result.

**Free functions** (from `from flywheelcad import *`, not methods on `cad`):

| Call | Returns | Notes |
|---|---|---|
| `region(loop=None, holes=None, inside=None, name=None)` | region | identical to `cad.region(...)` (§5); `name=` is a label only — a region is an intent, not a Ref. `inside=` takes a `cad.variable` expression per element (`inside=(w * 0.4, h * 0.2)`), resolved at script time exactly as a constructor's coordinate is |
| `rev(element)` | reversed element | for `loop=`/`chain=` traversal order (§5) |
| `ref(name)` | Ref | address an element by its string name (§4.6) |
| `sweep_section(fraction, plane, region)` | sweep keyframe | for `cad.sweep(sections=[...])` (§6.4) |

**Sketch context and geometry** (§4):

| Call | Returns | Notes |
|---|---|---|
| `cad.with_sketch(plane_name)` | — | sets the ambient plane for everything after it |
| `cad.origin(plane_name)` | Ref | the plane's origin point, e.g. `cad.origin("xy")` → `origin_xy`. `origin_xy`/`origin_yz`/`origin_zx` are also injected as globals automatically, as is `origin_<name>` for each custom plane |
| `cad.point(x, y, z)` | Ref | a **3D** reference point in world coordinates. A constructor stores **numbers**: a `cad.variable` expression is accepted but is evaluated at script time, so give every variable in it a `value=` |
| `cad.point2d(x, y)` | Ref | 2D, in the current sketch's coordinates; same rule — `cad.point2d(leg, 0)` resolves to the number and adds **no** constraint (a coordinate is the solver's starting guess, not a dimension) |
| `cad.line2d(p1, p2, construction=False)` | Ref | |
| `cad.circle2d(center, radius, construction=False)` | Ref | `cad.circle2d(ctr, hole_dia / 2)` emits the resolved radius **and** a `cad.radius(circle=c1, radius=hole_dia / 2)` after it, so the parametric link survives (that dimension has no script line, so edit the variable, not the annotation). Only for a **linear** expression — `w * h` or `a / b` between two variables builds the right circle but keeps no link |
| `cad.ellipse2d(focus1, focus2, point, construction=False)` | Ref | two foci plus a rim point |
| `cad.arc2d(center, start, end, clockwise=False, construction=False)` | Ref | endpoints must lie on the circle |
| `cad.spline2d(points, closed=False, construction=False)` | Ref | cubic spline through the points |
| `cad.text(string, size=10.0, font=…, at=(0,0), angle=0.0, direction=None, distance=None, align="left", quality=None, export=None, plane=None)` | list of Refs, one per character position | outline mode by default; `distance=<mm>` makes solid bodies (§4.7); `size`/`angle`/`distance`/`at`/`direction` all accept a `cad.variable` — its value is recorded at author time, so editing the variable later does not resize or move the glyphs |
| `cad.fillet(line1, line2, radius)` | Ref (the arc) | rounds a shared-endpoint corner (§4.6) |
| `cad.trim(element, near)` | `(element, split_piece)` | trims in place |
| `cad.create_sketch_plane(p1, p2, p3, name=None)` | plane | **always pass `name=`** (§6.8) |

**Constraints** — all return nothing *except* the two tangent-line constraints,
which produce a tangency point (§4.3). **Wherever one takes a POINT, a circle or arc
may be given instead and means its CENTRE** — all of them, not only `coincident`.

| Call | Returns |
|---|---|
| `cad.horizontal(line)` · `cad.vertical(line)` | — |
| `cad.parallel(line1, line2)` · `cad.perpendicular(line1, line2)` · `cad.collinear(line1, line2)` | — |
| `cad.coincident(p0, p1)` · `cad.merge_points(source, target)` | — |
| `cad.point_on_line(point, line)` · `cad.point_on_circle(point, circle)` · `cad.point_on_ellipse(point, ellipse)` · `cad.point_on_plane(point, plane)` | — |
| `cad.fixed(element)` | — |
| `cad.concentric(circle1, circle2)` · `cad.equal_lines(line1, line2)` · `cad.equal_radius(circle1, circle2)` | — |
| `cad.circle_tangent_circle(circle1, circle2)` | — |
| `cad.symmetry_line(p1, p2, symmetry_line)` · `cad.symmetry_plane(point1, point2, plane)` | — |
| `cad.circle_tangent_line(circle, line, anchor=None)` | **Ref — must be assigned** |
| `cad.ellipse_tangent_line(ellipse, line, anchor=None)` | **Ref — must be assigned** |
| `cad.spline_tangent_line(spline, line, control_point=None, control_point_index=None)` | — |

**Dimensions and variables** (§4.4, §4.5):

| Call | Returns | Notes |
|---|---|---|
| `cad.length(line, length)` · `cad.distance(p0, p1, distance)` · `cad.radius(circle, radius)` | — | value may be a number, variable or expression. A **dimension** is the only thing that stores an expression as one; a **constructor** (§B) takes the same spellings but resolves them to a number at script time |
| `cad.angle(line1, line2, angle=None)` | — | degrees |
| `cad.point_line_distance(point, line, distance)` | — | perpendicular distance |
| `cad.variable(value=None, fixed=False, driving=False)` | Ref | `fixed` and `driving` are **mutually exclusive** — both raises |
| `cad.fraction(refA, refB, multiplier)` | — | binds `refA = multiplier * refB` between two variables |
| `cad.update(changes)` | — | e.g. `cad.update({w: {"value": 60}})`, re-solves |
| `cad.ensure_convergence()` | — | force a solve of the current sketch |
| `cad.mirror_elements(elements, symmetry_line)` | — | copies are named `<source>_m` (§4.6) |

**Bodies** (§6). Every producer below also accepts `quality=`, `export=` and
`name=`; see **§C** before you use `quality=`:

| Call | Returns | Notes |
|---|---|---|
| `cad.extrude(plane, region, distance, direction=None, edge_radius=None, offset=None, draft=None, twist=None, twist_center=None)` | body | `direction` is `None`, `"positive"`, `"negative"` or `"symmetric"`; `offset` takes a `cad.variable` or expression like `distance` does, `edge_radius`/`twist`/`draft` take only a plain python number (a python variable holding one is fine) |
| `cad.revolve(plane, region, axis_line=None, angle=None, edge_radius=None)` | body | `angle=360` for a full solid |
| `cad.loft(start_plane=, start_region=, end_plane=, end_region=, edge_radius=None)` | body | keyword form strongly preferred (§6.3) |
| `cad.multi_loft(planes, regions, edge_radius=None)` | body | one seamless solid through N≥2 sections |
| `cad.sweep(plane=None, region=None, path=None, sections=None, twist=0.0, edge_radius=None)` | body | `sections=` and `plane=`/`region=` are mutually exclusive (§6.4); `twist`/`edge_radius` take only a plain python number (a python variable holding one is fine), as on `cad.extrude` |
| `cad.helix(radius, pitch, turns, axis_origin=(0,0,0), axis_dir=(0,0,1), start_angle=0.0, left_handed=False)` | **path handle** | `start_angle` is in **degrees**, and accepts a `cad.variable` (its value is recorded, not linked) |
| `cad.path(plane, chain)` | **path handle** | open planar rail; no closed elements |
| `cad.path3d(points, closed=False, up=None)` | **path handle** | points must be named 3D refs, not tuples; `closed=True` raises |
| `cad.bool_union(*bodies, blend=None, radius=None)` | body | ≥2 bodies; `blend` requires **exactly 2** and a positive `radius` |
| `cad.bool_difference(*bodies, blend=None, radius=None)` | body | first minus the rest |
| `cad.bool_intersection(*bodies, blend=None, radius=None)` | body | |
| `cad.offset(body, distance=None)` | body | positive grows, negative shrinks |
| `cad.move(body, translate=None)` | body | `translate=` is **keyword-only**; positional or `dx=`/`dy=`/`dz=` raises |
| `cad.rotate(body, axis=(0,0,1), angle=0, center=(0,0,0))` | body | |
| `cad.scale(body, factor=None, sx=None, sy=None, sz=None)` | body | |
| `cad.mirror_body(body, plane="yz")` | body | |
| `cad.copy(body)` | body | |
| `cad.pattern_linear(body, direction=(1,0,0), count=2, spacing=10)` | **list** `[seed, copy_1, …]` | `count` INCLUDES the seed; 2…1000; needs an assignment target or `name=` (§6.7b) |
| `cad.pattern_circular(body, axis=(0,0,1), count=4, angle=360, center=(0,0,0))` | **list** `[seed, copy_1, …]` | `angle` is the TOTAL sweep, non-zero, up to ±360° (§6.7b) |
| `cad.delete_body(body)` | — | cascades to consumers |

**Body properties** (§7). Each takes a `BodyRef`/`Ref` **or** a body-name string:

| Call | Chainable form | Notes |
|---|---|---|
| `cad.set_color(body, color, finish=None)` | `body.set_color(...)` | display only; written into 3MF (colour) and glTF/GLB (colour + finish as a PBR material) |
| `cad.set_export(body, value=True)` | `body.set_export(...)` | `value` must be a real `bool` |
| `cad.set_cell_size(body, cell_size)` | `body.set_cell_size(...)` | minimum `1e-6` mm — see **§C**. **No-op on a body that meshes EXACTLY** — an extrude or revolve with no `edge_radius` and no `draft` (a twist is still exact); there is no cell grid to refine. `quality=` (§9) is the knob there |
| `cad.hide(*bodies)` · `cad.show(*bodies)` | — (no chainable form) | variadic; zero arguments raises; hidden bodies are not exported |
| `cad.set_quality(quality)` | — | **document-wide — do not emit it; see §C** |
| `cad.set_units(units)` | — | `"mm"`\|`"cm"`\|`"in"`, presentation-only — **document-wide, do not emit it; see §C** |
| `cad.set_default_cell_size(cell_size)` | — | mm, minimum `1e-6` — **document-wide, do not emit it; see §C**. NOT the per-body `cad.set_cell_size(body, size)` one row above |


**Components and assemblies** (§8):

| Call | Returns | Notes |
|---|---|---|
| `with cad.component(name, label=None):` | context manager | `label` is a human-friendly display name shown in the UI |
| `cad.parametric(prefix, build, *, label=None, **params)` | component name | memoized per parameter set; `label` is keyword-only, is never passed to `build`, and does **not** contribute to the memoization key |
| `cad.component_name(prefix, *parts)` | str | the deterministic name `parametric` memoizes on |
| `cad.has_component(name)` | bool | whether that component was already emitted this run |
| `cad.component_export(body, name=None)` | — | marks an assembly-visible result |
| `cad.component_export_point(name, point)` | — | promotes a named anchor |
| `cad.instance(component, translate=None, mirror_plane=None, scale=None, axis=None, angle=None, center=None, export=None)` | instance ref | `center=` is the rotation pivot, used only with `axis`/`angle`. **`quality=` is accepted but silently dropped** with a warning — an instance inherits its component's quality |
| `cad.mate_coincident(instance, anchor, target, offset=None)` | — | closed-form snap |
| `cad.mate_align(instance, anchor1, anchor2, target1, target2, offset=None)` | — | snap + orient |
| `cad.mate(instance, anchor, target)` | — | solved 6-DOF pose; no `offset=` (§8.4) |
| `cad.mate_axis(instance, anchor1, anchor2, target1, target2)` | — | solved: the two axes made collinear, slide + spin left free; no `offset=` (§8.4) |



**Analysis** (§6.9): `cad.section(body, plane)`, `cad.project(body, plane)`,
`cad.project_point(point, plane)` — each returns a Ref and each accepts `name=`.


**GUI-emitted, do not hand-write:** `cad.label_offset(key, dx, dy)` records where
a user dragged a dimension label. It carries no geometry. Leave existing ones
alone when editing a document; never author one.

---

## C. Settings that belong to the app, not to your script

**Do not emit mesh-quality or document-unit configuration in a script you
generate.** Specifically:

1. **Never write `cad.set_quality(...)`.** This is the document-wide default and
   it is the app's to manage.
2. **Write a per-body `quality=` only when the geometry genuinely cannot resolve
   without it** — and then only on the specific body that needs it.
3. **Never write `cad.set_cell_size(...)` inside a loop, or through a variable
   that is rebound.**
4. **Never write `quality="precision"` as a document-wide setting.**
5. **Never write `cad.set_units(...)`.** This is the document-wide presentation
   unit and it is the app's to manage — GUI entry/readout conversion and 3MF
   export only (glTF/GLB export is always metres, whatever the unit), never
   a conversion of your geometry (see `FlyWheelCADSpec.md`
   §7.15). Your script's own numeric literals stay millimetres no matter what
   unit the document is set to.
6. **Never write `cad.set_default_cell_size(...)`.** This is the document-wide
   default meshing cell size and it is the app's to manage (View ▸ Default Cell
   Size…). It is a whole-document resolution commitment — it raises every
   body's cell budget, so a fine value costs memory and time on EVERY body. If
   one body needs a finer cell, use the per-body `cad.set_cell_size(body, size)`
   instead: one token apart in spelling, and the opposite in blast radius.

The rest of this section explains why each of those is a real constraint rather
than a style preference. The short version: **quality (and, identically, the
document unit) is a knob the user turns in the app, and the app turns it by
rewriting your script.** If your script writes that setting in a shape the app
cannot safely rewrite, you have not just chosen a default — you have permanently
disabled the control.

### Why: the app edits your script to change these settings

Because the script *is* the document, changing mesh quality in the UI is not a
model-only mutation. When the user picks a quality in the status bar or the View
menu, the app deletes every module-level `cad.set_quality(...)` statement and
inserts the canonical line immediately after the `cad = FlywheelCAD()` anchor,
then replays the whole script.

That rewrite is deliberately conservative: it parses before it touches anything,
and it refuses rather than guess. **Five shapes a generated script can take make
the refusal permanent** — the user clicks the quality menu, gets an alert, and can
never change quality from the UI again until someone hand-edits the file:

| What your script did | What the user is told |
|---|---|
| Put the call anywhere but a module-level statement — indented in an `if`, inside a `def`, on an assignment's right-hand side | "the script already has a `cad.set_quality(...)` call the app can't safely replace (it's indented inside a block or a function, or sits inside a larger expression). Edit that call directly" |
| Bound the handle to something other than `cad` at module level | "the script has no top-level `cad = FlywheelCAD()` line for the setting to sit after" |
| Imported an instanced component module **above** the anchor | "That import's own geometry is emitted at import time … so no position of the setting after the anchor can fix it. Move the import below `cad = FlywheelCAD()`" |
| Put the call on the same line as the anchor (e.g. via `;`) | "the existing call overlaps the line the setting has to be inserted after … Put the call on its own line" |
| Left a syntax error anywhere in the file | "the script has a syntax error … Fix it, then try again" |

Two of those are ordinary-looking generated code. `if detailed: cad.set_quality("ultra")`
and wrapping the build in `def main():` both look like good practice and both
break the user's quality picker for good.

**Omitting the line entirely is the correct default and needs no scaffolding.**
Absence means `standard`, as a stated invariant rather than an accident — the
executor resets to `standard` before every replay precisely so that deleting the
line reverts the document. When the user first changes quality, the app inserts
the line itself, in the right place. Your script does not need to prepare for that.

Two more rules make a hand-written line fragile even when it is well formed: it
must appear **before the first body-creating command anywhere in the script**
(because a body's curve tessellation is baked at creation time, so a later line
produces a half-applied state), it may appear **at most once**, and it may not
appear inside a `with cad.component(...)` block. Each violation fails the whole
run with a named error. §7 documents the rules in full for the case where you are
editing a document that already has one.

### Why: a per-body `quality=` silently overrides the user's picker

A per-body `quality=` kwarg wins over the document setting **by design** — that
is how an expensive tier is meant to be applied to the one body that needs it.
The cost is that a user who changes document quality and sees nothing happen has
no idea why. The app now says so, in the status bar ("N bodies use their own
quality — unaffected by this picker") and in the Body Inspector ("Pinned to Ultra
for this body — the document picker (currently High) does not apply") — **but the
View menu deliberately shows no such footnote**, so from there the skip is still
invisible.

So: pin a body's quality when the geometry demands it, and not otherwise. The
legitimate case is a feature that will not render at all at the inherited tier —
a real thread tooth, a sub-millimetre groove, a thin rib. §6.4 and §9 cover those.
A blanket `quality="high"` sprinkled across every body in a generated script is
the case to avoid: it looks harmless, and it makes the document's quality picker
appear broken.

If you do pin one, spell it as a **plain double-quoted literal on a single-line
call** — `cad.extrude("xy", r, 10, quality="ultra")`. A single-quoted string, a
variable, an expression, a duplicated kwarg or a multi-line call are all shapes
the Body Inspector's per-body picker cannot rewrite, so the user loses that
control too.

### Why: `precision` is expensive in ways that are not obvious

`"precision"` is the 1289-cell-budget tier. Three facts make it a poor default:

- **The budget is a ceiling, not a promise.** A large body is measured first and
  given the largest lattice up to 1289 that this machine's memory can actually
  serve; if even that does not fit, the quality ladder still steps down. The body
  is geometrically correct either way, but what you asked for is not what you
  necessarily get.
- **Its 0.1 mm cell size is a floor**, so precision is *identical to ultra* for
  any body small enough that ultra already reaches 0.1 mm. It differs only where
  the budget binds — on large parts, roughly above 13 cm. Applying it to small
  parts costs time and buys nothing.
- **The cost is measured, not theoretical.** A 15 mm control horn meshed at the
  old 1024³ budget took 863 seconds. One shipped sample spent 114 minutes, most
  of it on parts too small to benefit at all. Precision bodies mesh one at a time,
  and each retained mesh is on the order of 900 MiB — a multi-body assembly at
  document-wide precision can accumulate more resident memory than the machine has.

There is also a compatibility floor: `"precision"` has only been accepted since
2026-07-29, and **earlier builds refuse to open a document that sets it**.

### Why: `set_cell_size` through a loop or an alias breaks the inspector

`cad.set_cell_size(body, x)` is legitimate and sometimes necessary — it gives a
body an absolute cell size when a relative tier cannot resolve its small features
(§7). But the Body Inspector has to be able to attribute each `set_cell_size` line
to a specific body in order to offer a "clear" action. A line whose body argument
arrives through a loop variable, an alias, an expression, or a rebound name is
**unattributable**, and one such line blocks clearing the cell size for *every*
body in the document:

> "Line N sets a cell size on a body this editor can't identify (it goes through a
> variable, a loop, or an expression), so clearing this body's cell size can't be
> done safely — it might come back the next time the script runs."

`for w in wings: cad.set_cell_size(w, 0.8)` is the exact pattern to avoid, and it
is a natural thing for a generator to write. If several bodies need a cell size,
emit one line per body using either that body's own once-bound identifier or its
name as a string literal.

### Why: `cad.set_units(...)` is app-managed too

The View ▸ Document Units menu rewrites the script the same way View ▸ Mesh
Quality does: it deletes every module-level `cad.set_units(...)` statement and
inserts the canonical line after the `cad = FlywheelCAD()` anchor, then applies
it. The same refusal shapes apply — an indented/expression-form call, a handle
bound to something other than `cad`, a same-line `;` overlap, a syntax error —
with **one difference**: `set_units` has **no ordering requirement at all**
(nothing reads the document unit at command time), so unlike `set_quality`
there is no "before the first body" rule and no import-above-anchor decline to
worry about. Omitting the line is the correct default; absence means `mm`.

### Why: `cad.set_default_cell_size(...)` is app-managed too

Same machinery again (View ▸ Default Cell Size…), with `set_quality`'s rules
rather than `set_units`': the value is read when a swept body is BUILT, not
only when it is meshed, so the line **must precede the first body-creating
command**, may appear **at most once**, and may **not** live inside a
`with cad.component(...)` block. Two shapes decline that the string settings
do not: a computed **or signed** argument (`cad.set_default_cell_size(base / 2)`,
or a literal `-0.2`, which parses as a negation applied to a number) — the app
refuses to replace your expression with a literal — and a value below `1e-6`
mm, which is refused outright at both surfaces. Omitting the line is the
correct default; absence means "let the quality tier decide".

### What a good generated script contains

Nothing at all, in the normal case. No `cad.set_quality`, no `quality=`, no
`set_cell_size`, no `cad.set_units`, no `cad.set_default_cell_size`. The document opens at `standard`/`mm`,
every control in the app works, and the user tunes quality and units
themselves — which is both faster for them and the behaviour the app is
designed around. Add a per-body `quality=` or `set_cell_size` only where you
can name the feature that requires it, and say so in a comment.

---

## D. Author for the UI: real sketches, honest dimensions

**The file you produce is a document a person will open, inspect and edit — not
a build artifact.** Two scripts can emit byte-identical geometry and be worlds
apart in how usable the result is. A body whose profile was computed in python
and dropped in as bare coordinates is, in the app, an opaque solid: the user can
see it, hide it, colour it and export it, but they cannot ask *why it is that
size* or change it without editing your code. The same body built from a
constrained, dimensioned sketch opens, explains itself, and can be modified.

Aim for the second one. Concretely:

### 1. Build bodies from sketches, not from computed points

The pipeline (§1) already pushes you this way — draw 2D, identify a region,
extrude it. The failure mode is using that pipeline mechanically while doing the
real work in python: computing every vertex from a formula and emitting
`cad.point2d(...)` calls with literal results. It produces the right solid and an
unopenable sketch.

If a coordinate is the output of a calculation the *user* might want to redo,
the calculation belongs in the sketch as a constraint or a dimension, not in
python. If it is genuinely derived data (see §3 below), python is the right place.

### 2. Express intent as constraints, not just positions

Four points at exactly `(0,0)`, `(40,0)`, `(40,25)`, `(0,25)` *look* like a
rectangle. They are four unrelated points that happen to be arranged rectangularly,
and the first time anyone drags one, the shape stops being a rectangle. Two
`cad.horizontal(...)` and two `cad.vertical(...)` calls — four lines of script —
make it actually a rectangle, one that stays rectangular under edits.

Constraints are cheap and they are the part that encodes *design intent*:
`cad.horizontal` / `cad.vertical` for orthogonality, `cad.perpendicular` and
`cad.parallel` for relationships between edges, `cad.equal_lines` and
`cad.equal_radius` for "these are deliberately the same", `cad.concentric` for
shared centres, `cad.symmetry_line` for mirror symmetry about a construction axis.
Each one is a sentence about why the shape is the way it is, and each one survives
into the UI where the user can see it.

### 3. Dimension what a person would change — and nothing else

This is the part that needs judgement, and the failure runs in both directions.

**Dimension it** when changing the number is a *design decision*: overall width
and height, hole diameters, hole positions, wall thickness, bracket spacing, an
angle that matters, the length of a slot. These are the numbers someone opens the
document to adjust, and a dimension is what makes them adjustable in place.

**Do not dimension** geometry that is *sampled or derived*: the control points of
an aerofoil spline read from a coordinate table, glyph outlines produced by
`cad.text` (which are fixed, non-parametric splines by construction), points
generated inside a loop, or anything computed from a parameter you have already
exposed elsewhere. A 60-point aerofoil carrying 120 dimensions is not more
editable than one carrying none — it is dramatically less, because the sketch
becomes unreadable and no human edits an aerofoil by nudging point 37.

For sampled geometry, put the design decision **on the parameters that generated
the samples**, not on the samples. An aerofoil's editable numbers are chord,
span, thickness and twist — expose those as driving variables (§4) and let the
spline points be what they are: data.

The test to apply per number: *would a person open this document intending to
change this?* If yes, dimension it. If it is one sample among many, leave it
alone.

### 4. Use driving variables for the numbers that matter

A bare dimension pins a value. A dimension bound to a **driving variable** makes
it a named, reusable parameter — and the app has first-class UI for this: the
dimension binding form lets a user bind a dimension to an existing variable or
create a new one inline.

```python
w = cad.variable(40, driving=True)
h = cad.variable(25, driving=True)
cad.length(line=l1, length=w)
cad.length(line=l2, length=h)
cad.length(line=l3, length=w)      # the opposite edge follows the same variable
```

That last line is the point: the two long edges are not "both 40", they are
"both `w`". Editing `w` moves both. Expressions work too (`w * 0.5`), and
`cad.fraction(...)` binds two variables by ratio (§4.5).

> **Declare each variable immediately above the sketch it drives, not in one
> block at the top of the file.** A `cad.variable(...)` declared BEFORE a sketch
> that contains `cad.fillet(...)` is dragged off its value by that sketch's
> solve, silently: bound to a radius in a later sketch the circle comes out at
> roughly half its value, and bound to an extrude distance the body builds with
> zero thickness. Neither reports anything. The habit of declaring at the point
> of use side-steps it entirely and reads better regardless. Repro and the
> eliminations behind it: `plans/repro-variable-clobbered-by-fillet.md`.

One consequence worth knowing when you choose between them: a dimension bound
directly to a `cad.variable` is fully GUI-editable — the Edit Dimension sheet
shows the user the variable by name, so it can replace it with a number or
another variable. A dimension bound to an **expression** (`w * 0.5`) or to a
plain python variable is deliberately DECLINED by that sheet rather than
overwritten, because the sheet has no way to show the user what they would be
destroying. Both replay identically; the difference is only in what the GUI will
edit for you. See §6 below.

### 5. Aim for the green badge, but do not chase it

The sketch view carries a solver status badge with four states, and it is the
feedback loop for everything above:

| Badge | Meaning |
|---|---|
| **No constraints** (grey) | nothing has been said about the shape |
| **N DOFs free** (blue) | under-constrained — the solver can still move things |
| **Fully constrained** (green) | every degree of freedom is pinned |
| **Conflicting constraints** (red) | over-constrained — you have said the same thing twice, incompatibly |

Green on the shapes that carry design intent is the target: a fully-constrained
rectangle or hole pattern behaves predictably when edited. **Red is a real
failure** and is exactly what over-dimensioning produces — dimension a rectangle's
width, its opposite edge's width, and the distance between its two vertical
edges, and you have stated one fact three times.

Blue is **not** a failure. An aerofoil spline sitting at "40 DOFs free" is the
honest state for sampled geometry, and forcing it green would mean the
over-dimensioning §3 warns against. Constrain what is intentional; leave what is
sampled.

### 6. One mechanical requirement: module level

**Form no longer matters.** The app's in-place dimension edit (double-click a
dimension → Edit Dimension → Save) locates the line by what it MEANS — the
constraint name, the elements it names, and which parameter carries the value —
not by how it is spelled. All of these are GUI-editable, and each keeps its own
form and spacing when edited:

```python
cad.length(line=l1, length=40)     # keyword form
cad.length(l1, 40)                 # positional form
cad.length(l1, length=40)          # mixed
cad.length(l1, 40)  # 40 mm rail   # positional; trailing comments survive verbatim
cad.length(l1, 40);  cad.radius(c1, 8)   # positional; either statement can be edited
```

The edit replaces the VALUE and nothing else — the rest of the line comes back
byte for byte.

**A dimension bound to something the sheet cannot show you is declined, not
overwritten.** The Edit Dimension sheet displays a number (or a variable name,
for a dimension bound to one). If the script binds the value to a python-side
variable or an expression, the sheet has no way to show you that, so saving over
it would silently delete design intent. Instead the edit refuses and says what
it preserved:

```python
HOLE_DIA = 12.0
RAIL = 40.0
cad.radius(hole, HOLE_DIA / 2.0)   # positional; declined: the expression is preserved
cad.length(l1, RAIL)               # positional; declined: RAIL is a plain python variable
w = cad.variable(40, driving=True)
cad.length(line=l1, length=w)      # EDITABLE: the sheet shows you `w`
```

(A name bound through `cad.variable(...)` — like the showcase bracket's
`WIDTH` — IS shown by the sheet, and such a dimension stays fully editable;
only plain python names and expressions decline.)

> Couldn't update this dimension in the script: its value is written as
> "HOLE_DIA / 2.0", which this editor won't overwrite — it's a variable or an
> expression the sketch can't show you. The script still says "HOLE_DIA / 2.0".
> Edit the value in the script instead.

The last case is the important one: `cad.variable(...)` dimensions (§4.5) are
FULLY editable, in both directions — replace the variable with a constant, or
rebind it to another variable — because the sheet showed you the binding you are
replacing. That is the recommended style anyway.

**Module level still matters.** The matcher only looks at lines that start at
column 0, so an **indented** dimension — one inside a `with cad.component(...)`
block — is not GUI-editable, and neither is a dimension split across several
lines. If a number inside a component is meant to be tuned by the user, expose
it as a parameter of `cad.parametric(...)` rather than burying a dimension in
the block.

Finally, a dimension the document spells **more than once** — for example a
docstring or an example block that repeats the live line verbatim — is refused
as ambiguous rather than edited, since an in-place edit cannot tell which
occurrence you meant.

### 7. A worked contrast

Same plate, same solid, two very different documents.

```python
# OPAQUE — correct geometry, nothing to edit.
pts = [(0, 0), (40, 0), (40, 25), (0, 25)]
p = [cad.point2d(x, y) for x, y in pts]
ls = [cad.line2d(p[i], p[(i + 1) % 4]) for i in range(4)]
plate = cad.extrude("xy", region(loop=ls, inside=(3, 3)), 8)
```

```python
# EDITABLE — same solid, and the document explains itself.
w = cad.variable(40, driving=True)     # plate width
h = cad.variable(25, driving=True)     # plate height

cad.with_sketch("xy")
p1 = cad.point2d(0, 0);  p2 = cad.point2d(40, 0)
p3 = cad.point2d(40, 25); p4 = cad.point2d(0, 25)
l1 = cad.line2d(p1, p2); l2 = cad.line2d(p2, p3)
l3 = cad.line2d(p3, p4); l4 = cad.line2d(p4, p1)

cad.horizontal(line=l1); cad.horizontal(line=l3)    # it IS a rectangle
cad.vertical(line=l2);   cad.vertical(line=l4)
cad.length(line=l1, length=w)                       # the two numbers that matter
cad.length(line=l2, length=h)

centre = cad.point2d(20, 12.5)
hole = cad.circle2d(centre, 5)
cad.radius(circle=hole, radius=5)                   # a design decision: dimension it

plate = cad.extrude("xy", region(loop=[l1, l2, l3, l4], holes=[[hole]],
                                 inside=(3, 3)), 8)
```

The second costs eight extra lines. In exchange the user can open the sketch, see
that it is a constrained rectangle with a dimensioned hole, change `w` from 40 to
55, and watch the plate rebuild — without reading a line of python.

---

## 1. The model in 60 seconds

- A FlywheelCAD **document _is_ a Python script.** Opening it re-executes the
  script to rebuild the geometry; saving writes the script. There is no separate
  binary model — **the script is the source of truth.** Write scripts that fully
  reconstruct the design from scratch, deterministically.

  (A document is either a flat `.py` or a `.fwcad` project bundle — a folder whose
  `main.py` is the script. The API is identical either way; **deliver a bundle** — see §A.)

- Because the script is the document, **the app edits your script** when the user
  changes a setting in the UI. Write code the app can safely rewrite — §C.
- The script doesn't manipulate the model directly. Each `cad.*(...)` call
  **emits a command**; the host runs them in order: solve 2D sketches with a
  constraint solver, then build 3D solids.
- The pipeline is always **2D sketch → region → 3D solid**. You draw constrained
  2D geometry on a plane, identify a closed **region**, then `extrude`/`revolve`/
  `loft` it into a body. Bodies combine via booleans and transforms.
- Units are unitless numbers (treat as millimetres). Angles are **degrees**.

---

## 2. File skeleton

Every script starts the same way — this is the whole preamble of a bundle's `main.py`, and
it is exactly what the app writes for a new document:

```python
# flywheelcad-format: 1
from flywheelcad import *
cad = FlywheelCAD()

# ... build the design ...
```

That's the entire boilerplate. The format stamp is optional (§A) but free.
The third line repays a closer look:

- **The handle must be bound to the name `cad`, at module level.** Several app
  features locate that exact assignment as an anchor — most visibly the mesh
  quality setting, which is inserted immediately after it. A handle named
  anything else, or created inside a function, disables those features (§C).

- **Put every `import` of a component module BELOW the anchor.** An imported
  component emits its geometry at import time, so an import above the anchor
  produces geometry the app cannot position a document setting before.


`from flywheelcad import *` also brings in the free functions used throughout:
`region(...)`, `rev(...)`, `ref(...)` and `sweep_section(...)`, plus the
`FlywheelCAD` class itself. It also injects an origin point per standard plane —
`origin_xy`, `origin_yz`, `origin_zx` — and one per custom plane as you create it
(§4.1).

---

## 3. Rules an agent MUST follow

These prevent the most common generation errors:

1. **Assign every created element to a distinctly-named variable.** The element's
   internal name is derived from the **left-hand-side variable name** via source
   introspection. `l1 = cad.line2d(p1, p2)` names the line `l1`. Then reference it
   as `l1` everywhere else.
   - Use unique names. Don't reuse a variable for two different elements.
   - Don't rename via plain aliasing (`x = l1`) and expect a new element.
   - Rebinding a body variable to a boolean over itself (`shaft = cad.bool_difference(shaft, tool)`) works and numbers both bodies (`shaft_1`, `shaft_2`; the variable ends on the result) — a string-form setter like `cad.set_export("shaft", False)` then matches no body, so use the variable or a distinct name; `name=` may not repeat an operand's name.
2. **Order matters.** A line needs its points first; a region needs its boundary
   elements; a body its region; a boolean its inputs; a mate the instances and their exported anchors. Emit in dependency order.
3. **Set the sketch plane before drawing 2D geometry:** `cad.with_sketch("xy")`.
   All subsequent `point2d/line2d/...` land on that plane until you switch.
4. **Plane names are the strings `"xy"`, `"yz"`, `"zx"`** for the three standard
   planes. Custom planes are refs returned by `cad.create_sketch_plane(...)`.
5. **Coordinates in `point2d` and `region(inside=...)` are 2D sketch coordinates**
   on the current plane, not world coordinates.
6. **Re-execution must be deterministic.** No `random`, no wall-clock, no reading
   external state that changes between runs. Helper functions and loops are fine
   and encouraged for repetitive geometry.
7. **Do not emit mesh-quality or document-unit configuration.** No
   `cad.set_quality(...)`; a per-body `quality=` only where a named feature
   demands it; no `cad.set_cell_size(...)` through a loop or alias; no
   `cad.set_units(...)`. These are the user's controls, and the app changes
   them by rewriting your script — write it in a shape the app can rewrite.

   **§C explains this in full; it is the rule most often got wrong.**

8. **Never put a construction element in a region loop.** Construction elements
   are excluded from region detection, so a loop containing one never closes. If
   you want a construction axis (for `revolve`, for symmetry), offset the profile
   so it does not touch the axis, and build the loop from real geometry.
9. **Sweep profiles are drawn centred at the sketch origin.** The profile's 2D
   coordinates are used unchanged as the offset from the path at every station,
   so a profile drawn out at the coil radius double-counts it. The offset lives
   in the path, never in both places (§6.4).
10. **Always pass `name=` to `cad.create_sketch_plane(...)`.** That name is the
    plane's identity for every later reference. Without it, planes auto-number in
    creation order, so inserting one earlier plane renumbers every later
    reference (§6.8).

11. **Inside a `with cad.component(...)` block, pass `plane=` explicitly** (or
    call `cad.with_sketch(...)` inside the block) for anything that takes a
    plane. Whether the block inherits the enclosing ambient plane depends on
    whether the component ends up instanced, which the script cannot always know
    in advance (§4.7).

12. **Assign the tangent-line constraints.** `cad.circle_tangent_line(...)` and
    `cad.ellipse_tangent_line(...)` produce a tangency point and raise
    `ValueError` unless the result is assigned to a variable or given an explicit
    `name=` (§4.3).
13. **A typo'd topology attribute is silent.** `body.v9999` cheerfully returns a
    ref; nothing fails until the name proves unresolvable much later. Verify
    topology names against the body you actually built, or use `cad.point(x,y,z)`
    and `create_sketch_plane` for reference geometry (§6.8).
14. **Build bodies from constrained, dimensioned sketches — not from computed
    coordinates.** The output is a document someone will open and edit, so
    express intent with constraints and dimension the numbers a person would
    want to change, while leaving sampled geometry (spline data, glyph outlines,
    loop-generated points) undimensioned. Write dimensions at **module level**
    (either form — keyword or positional — is GUI-editable), and give the
    numbers a user should tune a `cad.variable(...)` rather than a bare python
    variable or an expression, which the GUI declines to overwrite. A
    constructor stores a **number**, so a variable expression handed to one
    (`cad.circle2d(ctr, hole_dia / 2)`) is resolved at script time — legal, but
    the intent survives only where a linear dimension carries it (§B, §4.4). Pass
    the ref or expression itself; a `cad.variable` is a SYMBOL with no readable
    number (`v.value` raises). See §D for the judgement call and mechanics.
15. **Model each body as ONE profile whenever the shape allows — one region
    with its holes, one `extrude` or `revolve`.** A boolean between separately
    built bodies is exact in geometry but its result can carry a few
    non-manifold edges where the two surfaces meet (a cut cylinder's rim, a
    slot's rounded end, a plate seam), and that fails a watertightness check.
    Region holes and single profiles do not. Recipes:
    - plate / bar with round holes or slots → the holes and the slot outline
      (two lines + two arcs) go in `holes=`, one extrude;
    - L-bracket, T-block, stepped block → draw the L / T / stepped outline as
      the profile on the plane that shows it, extrude the width;
    - shaft, knob, flange, pulley, any stack of round sections → ONE `revolve`
      of the half-profile (steps included; a through-bore is the gap between
      the profile and the axis), never a union of cylinders;
    - keep booleans for what a single profile cannot express — a counterbore
      in a rectangular plate, a cross-drilled hole, a keyway, a pocket in a
      face — and over-span those tools (§10). Stacking two extrudes with
      different holes and unioning them is NOT a substitute: the flush seam
      is a boolean too.
16. **A later closed loop drawn INSIDE an earlier region's loop, on the SAME
    sketch, invalidates that earlier region.** Declare it under `holes=`, or
    draw the later profile on its own plane (`cad.create_sketch_plane`). The
    refusal names the offending loops and the remedies (§10).

---

## 4. Sketching (2D)

### 4.1 Planes & sketch context

```python
cad.with_sketch("xy")     # draw on the standard XY plane (also "yz", "zx")
# ... 2D geometry here ...
cad.with_sketch("yz")     # switch planes; later geometry lands on YZ
```

**Sketch axes and extrude direction — measured, not guessable from the name.**
A sketch point `point2d(x, y)` lands at `origin + x·u + y·v`; an extrude goes
along `+n` (`direction="negative"` along `−n`, `offset=` shifts the start along
`n`):

| plane | u (sketch x) | v (sketch y) | n (extrude) |
|---|---|---|---|
| `"xy"` | +X | +Y | +Z |
| `"yz"` | +Y | +Z | +X |
| `"zx"` | **−X** | +Z | +Y |

So a bore along Y through a block centred on the origin is a circle at
`point2d(-cx, cz)` on `"zx"`, extruded `+Y`; put the body in +X, +Y, +Z or
centre it on the origin and this stays easy to check. A custom plane from
three points follows the same rule: `n = (p2 − p1) × (p3 − p1)` (right-hand
rule), `v` = the plane's upward direction (+Z projected into the plane; +Y
when the plane is horizontal), `u = v × n`. Points `(0,0,0), (1,0,0),
(0,0,1)` therefore give `n = −Y`, `u = +X`, `v = +Z`.

**Each plane has an origin point you can constrain to.** `cad.origin("xy")`
returns it, and the same points are injected into your module's globals
automatically as `origin_xy`, `origin_yz` and `origin_zx` — plus `origin_<name>`
for every custom plane, created when you `cad.with_sketch(...)` to it. This is the
only way to constrain geometry to a plane's origin, and is often the right anchor
for an otherwise-free profile:

```python
cad.with_sketch("xy")
c = cad.circle2d(cad.point2d(0, 0), 5)
cad.coincident(p0=c, p1=origin_xy)   # a circle/arc means its CENTRE in ANY point argument, not just here (§B)
```

**A custom plane at height `z`, parallel to XY** (sketch axes +X, +Y) — how to put a second profile on top of a body without touching the first sketch:

```python
p0 = cad.point(0, 0, 6)
px = cad.point(1, 0, 6)
py = cad.point(0, 1, 6)
top = cad.create_sketch_plane(p0, px, py, name="top")
cad.with_sketch("top")
boss_circle = cad.circle2d(cad.point2d(0, 0), 10)
boss = cad.extrude("top", region(loop=[boss_circle], inside=(0, 0)), 10)
```

Any three non-collinear 3D points define a plane the same way (an oblique face,
a plane through an axis). After an extrude, the body's far-face vertices are
also available as 3D points (`box.v0`, `box.v1`, ...), but explicit
`cad.point(x, y, z)` references are easier to get right.

### 4.2 Primitives

All 2D primitives take/return points and live on the current sketch:

```python
p1 = cad.point2d(0, 0)                      # a 2D point
l1 = cad.line2d(p1, p2)                      # a line between two points
c1 = cad.circle2d(center_pt, radius=10)      # circle (center point + radius)
e1 = cad.ellipse2d(focus1, focus2, point)    # ellipse from two foci + a rim point
a1 = cad.arc2d(center, start, end, clockwise=False)   # arc; endpoints on the circle
s1 = cad.spline2d([p0, p1, p2, p3], closed=False)     # cubic spline through points

# 3D reference points (world coords) — for custom planes / anchors:
P = cad.point(10, 0, 5)
```

Add `construction=True` to any primitive to make it a **construction element**
(guides/axes/symmetry lines; rendered dashed, excluded from region detection):

```python
axis = cad.line2d(b, t, construction=True)
```

`cad.trim(element, near=(x, y))` trims in place at the nearest intersection and
returns `(element, split_piece)`; the original variable becomes the surviving
piece.

### 4.3 Geometric constraints

Most constraints return nothing — they are pure statements:

```python
cad.horizontal(line=l1);  cad.vertical(line=l2)
cad.parallel(line1=l1, line2=l2);  cad.perpendicular(line1=l1, line2=l2)
cad.collinear(line1=l1, line2=l2)
cad.coincident(p0=p1, p1=p2)           # merge two points
cad.point_on_line(point=p, line=l)     # point= (like every point argument) also takes a circle/arc = its CENTRE
cad.point_on_circle(point=p, circle=c);  cad.point_on_ellipse(point=p, ellipse=e)
cad.point_on_plane(point=p, plane="xy")
cad.fixed(element=l1)                  # pin an element's positional DOFs (arc: centre+radius, not endpoints)
cad.concentric(circle1=c1, circle2=c2)
cad.equal_lines(line1=l1, line2=l2);  cad.equal_radius(circle1=c1, circle2=c2)
cad.circle_tangent_circle(circle1=c1, circle2=c2)
cad.spline_tangent_line(spline=s, line=l)
cad.symmetry_line(p1=a, p2=b, symmetry_line=axis)
cad.symmetry_plane(point1=a, point2=b, plane="yz")
```

**Two constraints are different: they PRODUCE a tangency point and must be
assigned.** `cad.circle_tangent_line` and `cad.ellipse_tangent_line` mint a Ref
for the point where the line touches the curve, so — like every other
Ref-producing call — they derive their name from the left-hand side and raise
`ValueError` if there is no left-hand side to derive from:

```python
tp1 = cad.circle_tangent_line(circle=c, line=l)              # the tangency point
tp2 = cad.ellipse_tangent_line(ellipse=e, line=l, anchor=(12.0, 4.0))
```

Calling either without assigning it fails immediately with
`ValueError: circle_tangent_line must be assigned to a variable, for example
`p = cad.circle_tangent_line(...)``. An explicit `name=` satisfies the
requirement instead, if you need the call as a bare statement. The optional
`anchor=(x, y)` seeds which of the two tangency solutions the solver converges
to — give it when the curve and line admit two tangent points and you care which.

`cad.spline_tangent_line` takes two further optional kwargs that select **which**
control point the tangency applies at: `control_point=` (a point ref) or
`control_point_index=` (an integer). These are what the GUI emits, and both
replay correctly.

**Which form to write.** The keyword form above is the canonical dialect: it is
what the app itself writes into a document when you place a constraint in the
GUI, so a hand-written script and a GUI-authored one read identically. The
positional form is also accepted by every constraint and is what the bundled `Samples/` and `TestProjects/` scripts use (`Library/` is body/primitive factories and declares no sketch constraints at all):

```python
cad.horizontal(l1)                     # positional form, also accepted
cad.parallel(l1, l2)                   # positional form, also accepted
```

Prefer keyword when you can: the arguments of `parallel`, `perpendicular`,
`collinear`, `equal_lines`, `concentric` and `equal_radius` are same-typed, so a
positional call silently binds the wrong way round if the signature is ever
reordered, whereas a keyword call fails loudly.

### 4.4 Dimensions (pin a measured value)

```python
cad.length(line=l1, length=40)                  # line length
cad.distance(p0=a, p1=b, distance=25)           # EUCLIDEAN point-to-point. To hold a radius from an
                                                # axis use point_line_distance against the axis line
cad.radius(circle=c1, radius=8)                 # circle radius
cad.angle(line1=l1, line2=l2, angle=90)         # angle between two lines (degrees)
cad.point_line_distance(point=p, line=l, distance=5)  # point=/p0=/p1= also take a circle or arc, meaning its CENTRE
```

The positional form is accepted here too, and is what the bundled samples use:

```python
cad.length(l1, 40);  cad.distance(a, b, 25);  cad.radius(c1, 8)   # positional form, also accepted
```

Both forms — and each statement of a `;`-joined line like the one above — are
equally editable from the GUI, as long as the call sits at module level (§D.6).

A value can be a number, a **variable**, or an **expression** of variables. A
number or a `cad.variable` is GUI-editable; an expression is preserved rather
than overwritten when the user edits that dimension (§D.6).

### 4.5 Variables (parametric dimensions)

```python
w = cad.variable(40, driving=True)   # editable driving dimension (default for params)
cad.length(line=l1, length=w)        # bind a dimension to it
cad.length(line=l2, length=w * 0.5)  # expressions work (+, -, *, /); ** resolves to a number (no exponent in the document grammar), losing the link

# fixed=True  -> permanent constant (never moves)
# driving=True -> pinned during solves but editable via the UI / cad.update(...)
# (neither)    -> a free unknown the solver may move
```

`fixed=True` and `driving=True` are **mutually exclusive** — passing both raises
`ValueError`. Pick one, or neither.

Edit a driving value programmatically (re-solves afterward):

```python
cad.update({w: {"value": 60}})
```

**Bind one variable to another by ratio** with `cad.fraction(refA, refB, multiplier)`,
which enforces `refA = multiplier * refB`. This is the only way to express a
proportional relationship *between two variables* — dimension expressions like
`w * 0.5` bind a dimension to an expression, whereas `fraction` constrains the
variables themselves, so the relationship survives edits to either side:

```python
span  = cad.variable(200, driving=True)
chord = cad.variable(50,  driving=True)
cad.fraction(chord, span, 0.25)     # chord is always a quarter of span
```

### 4.6 Other sketch ops

```python
# Each mirrored element (and its defining points) is registered under a
# derived name `<source>_m` — e.g. mirroring `l1` names the copy `l1_m`,
# addressable later via `ref("l1_m")`. Mirroring the SAME source again
# (e.g. across a second axis) names the next copy `l1_m2`, then `l1_m3`,
# etc. — the smallest name not already claimed by a live element,
# reproduced identically on replay because it is based on what objects
# EXIST at that point in the script, not on script text or bookkeeping.
cad.mirror_elements([l1, l2, c1], symmetry_line=axis)   # mirror elements across a line
cad.merge_points(p_src, p_dst)                  # weld two points
cad.ensure_convergence()                        # force a solve of the current sketch

# Round the corner where two elements (lines OR arcs, any mix) share an
# endpoint: both retract to the tangent points and a tangent arc bridges them
# (tangency + radius are constrained, so the fillet stays valid on re-solve).
# The element variables keep referring to the retracted elements; the returned
# arc goes into region loops between them: region(loop=[l1, f1, l2, ...]).
# Rejected when the join is already tangent-continuous (no corner) or the
# radius doesn't leave part of both elements.
f1 = cad.fillet(l1, l2, radius=4)
f2 = cad.fillet(l3, a1, radius=2)   # line–arc and arc–arc corners work too
```


### 4.6b Repeating sketch geometry (no sketch pattern OPCODE; Modify ▸ Pattern… writes this)

Write the loop; constrain each copy to the SOURCE, never its predecessor — two constraints per copy make it parametric (move the source, every copy follows). There is no `cad.pattern_*` for sketch geometry: the GUI's **Modify ▸ Pattern…** emits precisely this block, circular or row, for points, lines, circles, arcs and ellipses (`ring`/`polar`/`grid` are pure and emit nothing). Circular = `equal_lines` + `angle` per copy; row = `length` + a zero `angle` against a line the row cannot move — never `cad.parallel`, which lets a copy flip sides. Arcs pin both ends via their radius, so star the centre and ONE end. `cad.pattern_linear`/`pattern_circular` stay BODY ops (§6.7b). Full recipe with code: the manual's "Repeating sketch geometry" callout.

```python
step = cad.variable(60, driving=True)        # editable; `fixed=True` would fold it flat
c = cad.point2d(0, 0)
p0 = cad.point2d(25, 0)
l0 = cad.line2d(c, p0, construction=True)    # the SOURCE every copy is constrained to
for k, angle in enumerate(ring(6)):          # ring/polar/grid are PURE, emit nothing
    if k == 0:
        continue
    pk = cad.point2d(*polar(25, angle))
    lk = cad.line2d(c, pk, construction=True)
    cad.equal_lines(line1=l0, line2=lk)
    cad.angle(line1=l0, line2=lk, angle=step * k)
```

### 4.7 Text

Render a string as glyph outlines in the current sketch — or straight into
solid bodies:

```python
refs = cad.text(string, size=10.0, font="Helvetica", at=(0.0, 0.0), angle=0.0,
                direction=None, distance=None, align="left",
                quality=None, export=None, plane=None)
```

- `size` is the target **cap height** in mm (calibrated against the font's
  measured cap height, not its raw em-square — capitals come out ~`size` mm
  tall in any font).
- `plane` (optional) picks the sketch plane the glyph outlines/bodies are
  built on. Defaults to whatever the most recent `cad.with_sketch(...)`
  selected (`"xy"` if `with_sketch` was never called) — the same "current
  sketch plane" every other body op (`extrude`, `revolve`, `sweep`, ...)
  follows. **Inside a `with cad.component(...):` block, that default depends
  on whether the component ends up transparent or instanced.** A component
  that is never `cad.instance(...)`d (transparent) runs on the TOP-LEVEL
  executor, so a plane-less `cad.text(...)` inside it inherits whatever
  `with_sketch` the ENCLOSING scope last called. A component that IS
  instanced runs its block on a fresh sub-design/executor whose own ambient
  starts at `"xy"`, with no outer plane visible at all. Since a script can't
  always know ahead of time whether a given component will end up
  instanced, pass `plane=` directly (or call `with_sketch` inside the block)
  to be immune to the distinction.
- Passing `plane=` explicitly builds the text on that plane **without**
  switching the ambient current sketch. If that plane isn't the one shown in
  the 2D sketch view, the new outline splines won't be visible there until
  you `cad.with_sketch(...)` to it — the body still meshes and renders in 3D
  either way.
- **Outline mode** (`distance=None`, the default): each glyph's closed contours
  drop into the current sketch as **fixed (non-parametric) splines**. A glyph's
  counters are its holes when the glyph's OUTLINE is the region's loop and the
  region declares no `holes=` (`region(loop=[glyphs[0]])`); a region that does
  declare holes must list the counters too, as strings (`"t_0_h0"`).
- **Solid mode** (`distance=<mm>`, must be `> 0`): additionally extrudes each
  glyph (counters cut as holes) into its **own body** on the current plane,
  `distance` mm deep. One body per glyph — glyphs are **NOT unioned**; call
  `cad.bool_union(...)` yourself if you want one solid.
- `align` (`"left"`/`"center"`/`"right"`) positions the run relative to `at`,
  the baseline-origin point in the current sketch's mm coordinates. `angle`
  (degrees, CCW-positive) rotates the whole run about `at`; `direction=(dx, dy)`
  is sugar that derives `angle` from a vector (e.g. `direction=(0, 1)` runs the
  text up +Y).
- Returns one `Ref` **per character position** in `string` (outer contour
  spline in outline mode; the glyph body in solid mode). A position with no
  visible glyph (e.g. a space) creates nothing — that `Ref` simply won't
  resolve if referenced, same as a typo. Hole/counter contours are still
  created and individually addressable as `<name>_<i>_h<k>` even though they
  aren't returned.
- Naming: the base name comes from the LHS variable as usual (auto `t` counter
  — `t1`, `t2`, … — when there is none, e.g. GUI-authored lines); per-glyph
  refs/bodies append the position index: `t1_0`, `t1_1`, …. Known gap:
  glyph-body vertices (`t1_0_v0`) do not yet dot-convert for the python
  `BodyRef` attribute syntax (`topology-dot-notation-body-kinds` in TODO.md).

```python
# Outline mode: a word as sketch splines, then extruded through a region.
cad.with_sketch("xy")
glyphs = cad.text("HUB", size=12, at=(0, 0))
label = cad.extrude("xy", region(loop=[glyphs[0]]), 3)   # extrude the "H"

# plane= builds on a plane other than the current sketch, no with_sketch needed.
tag = cad.text("A1", size=6, distance=1, plane="angled")
```


---

## 5. Regions — the bridge from 2D to 3D

A **region** is the closed area a solid is built from. It is identified by a
**directed boundary loop**, optional **holes**, and an optional **inside point**:

```python
r = cad.region(
    loop=[l1, l2, l3, l4],     # ordered boundary; consecutive elements share endpoints
    holes=[[hole_circle]],     # list of hole loops (each a list of elements)
    inside=(x, y),             # a point KNOWN to be inside the material (2D coords)
)
```

- `loop` is **directed**: list the boundary elements in traversal order. If an
  element runs against its natural direction in the loop, wrap it with `rev(...)`:
  `loop=[c1, rev(l4)]`.
- `holes` cut material; each hole is its own loop list — if a bore is also a hole in another region, reuse the SAME circle/arc in both rather than drawing a second one at the same centre and radius: a second coincident circle/arc is silently dropped as a duplicate, so the region naming the surviving one resolves but the region naming the dropped duplicate can never resolve.
- `inside=(x, y)` disambiguates when one boundary could enclose two areas (e.g.
  concentric circles). Give a point clearly in the solid material. You can omit it
  when the loop is unambiguous, but **including it is safer** — always include it
  for any region with holes or multiple candidate faces. Either element may be a
  `cad.variable` expression (`inside=(w * 0.4, h * 0.2)`), resolved at script
  time; a witness has no parametric link to lose.
- An `inside=` point that falls **inside a hole** asserts the hole is filled: the
  region resolves to the material reading that includes that spot (this is how a
  plugged hole is expressed). A witness in ordinary material never relaxes hole
  strictness.
- **Every closed loop inside the region's loop is declared under `holes=`, or an `inside=` witness inside it claims it as material, or the region is REFUSED** — the refusal names the loops and the remedies. A glyph's counters, when the glyph's own outline is the region's loop, are the one exception.

`region(...)` (top-level) and `cad.region(...)` are equivalent.

---

## 6. Bodies (3D)

Every body call returns a **body ref** (e.g. `body1`) you reuse downstream.
Common keyword args across body ops: `edge_radius=` (uniform fillet), `export=`
(pass `False` to exclude from mesh export), `name=` (override the derived name),
and `quality=` (`"preview"`/`"standard"`/`"high"`/`"ultra"`/`"precision"`).
`cad.text(...)` in solid mode (`distance=<mm>`) also creates bodies — one per
glyph (see §4.7).

> **Before you write `quality=` anywhere, read this.** In a generated script it
> should appear only on a body whose geometry cannot resolve without it, and
> `cad.set_quality(...)` should not appear at all (see §C). `export=` accepts only a real
> `bool`; a string or `0`/`1` raises `ValueError`.

### 6.1 Extrude

```python
body = cad.extrude("xy", region, distance,
                   direction=None,      # see below; None = one-way along +normal
                   edge_radius=None,    # fillet all edges by this radius
                   offset=None,         # shift off the plane along the normal; variable/expression OK
                   draft=None,          # taper walls by this angle (deg); + = outward
                   twist=None,          # total twist (deg) of the cross-section over the height
                   twist_center=None,   # 2D pivot for the twist (default: region centroid)
                   quality=None, export=None, name=None)
```

`direction=` accepts **four** values, not two: `None` (one-way along the plane's
+normal), `"positive"` (the same thing, stated explicitly), `"negative"` (one-way
along the −normal), and `"symmetric"` (equal distance both ways). Any other string
is refused with an error naming the legal set.

The optional numeric kwargs default to `None`, not `0`: each is emitted only when
non-zero, so omitting one and passing `0` differ only in the written-back script.
`distance`/`offset` take a `cad.variable` or an expression over one; `edge_radius`/`twist`/`draft` refuse those, but a plain python number — or a python variable holding one — is fine there.

### 6.2 Revolve

```python
rbody = cad.revolve("xy", region, axis_line, angle,   # axis_line is a (construction) line; angle in degrees
                    edge_radius=0, quality=None)
# angle=360 for a full body of revolution; <360 for a partial revolve.
```

### 6.3 Loft & multi-loft

```python
# Two profiles on two (possibly non-parallel) planes. ALWAYS use the keyword
# form: the four profile arguments are two same-typed pairs, so a transposed
# positional call silently lofts the wrong way rather than failing. (A
# positional call does work end-to-end from python — the emitted line always
# carries the keyword names — but you lose the one safeguard that catches a
# transposition, for no benefit.)
lbody = cad.loft(start_plane=start_plane, start_region=start_region,
                 end_plane=end_plane, end_region=end_region, edge_radius=0)

# One smooth solid through N>=2 sections (no internal seams) — preferred over
# chaining 2-section lofts + unions:
mbody = cad.multi_loft([plane0, plane1, plane2], [region0, region1, region2])
```

Both profiles must have the same number of holes. `multi_loft` interpolates a SMOOTH surface through its sections, so two equal sections followed by a smaller one bulge outward between the equal pair (a 30 mm base measured 30.7 mm). For straight-walled stacks of round sections use one `revolve`; a loft is for a genuinely blended transition.

### 6.4 Sweep & paths (helix / path / path3d / sections)

```python
path = cad.helix(radius=8, pitch=4, turns=5,           # coil radius/rise/turn-count
                 axis_origin=(0, 0, 0), axis_dir=(0, 0, 1),
                 start_angle=0.0, left_handed=False)   # a PATH HANDLE, not a body
rail = cad.path("xy", chain=chain)                     # planar open-chain rail (below)
rail3 = cad.path3d(points, closed=False, up=None)      # 3D free-curve rail (below)
sbody = cad.sweep("xy", region, path, sections=None, twist=0.0,
                  quality=None, export=None, edge_radius=None, name=None)
```

`cad.helix`'s `start_angle=` is in **degrees**, like every other angle in this
API.

There are three path constructors — `cad.helix`, `cad.path`, `cad.path3d` —
and each returns a **path handle** for `cad.sweep(path=...)`, never a body;
`cad.sweep` returns the body.

**`name=` is universal.** Every `cad.*` call that mints a Ref accepts an optional
`name=` — the 2D primitives, `text`, `fillet`, `variable`, every body producer,
the path constructors, the two tangent-line constraints, `instance`, and `section`/`project`/`project_point`.
It overrides the usual naming (derived from
the left-hand-side variable, or an auto counter like `path1`, `sbody1`, … when
there is none), which is useful when a script wants a predictable, human-readable
symbol. A name that collides with an existing symbol raises `ValueError`.
`region(...)` also takes `name=`, but only as an inert python-side label — not validated,
not checked for collisions, never written into a command (a warning line says so).

Exceptions worth knowing. `cad.create_sketch_plane(...)` takes `name=` too,
but there it is effectively **required** rather than optional (§6.8) — a plane is
referenced by bare string everywhere afterwards.

And `cad.component(...)` / `cad.parametric(...)` mint *component* names, which
are plain strings rather than Refs, by a different mechanism: they do not take
`name=`, but both take `label=` for a human-friendly display name (§8.1).


**Anchoring convention (read this before using sweep — it is the #1 mistake):**
the profile's 2D `(x, y)` are used AS-AUTHORED, UNCHANGED, as the local
`(u, v)` offset from the path at every station — the sketch plane supplies 2D
geometry only, NOT 3D placement. A profile drawn AT THE SKETCH ORIGIN rides
exactly ON the path; the path's own `radius=` supplies the coil offset. **Do
NOT also draw the profile out at the coil radius — that double-counts it.**
`(u, v)` maps to the path frame's `(normal, binormal)`, where `normal` is
radially outward from the helix axis.

```python
# A spring: a small wire circle, drawn CENTERED AT THE SKETCH ORIGIN.
cad.with_sketch("xy")
origin = cad.point2d(0, 0)
wire = cad.circle2d(origin, 1.2)                 # profile radius, NOT the coil radius
r1 = region(loop=[wire], inside=(0, 0))
path1 = cad.helix(radius=8, pitch=4, turns=6)     # coil radius lives on the PATH
spring = cad.sweep("xy", r1, path1, quality="high")


# A real ISO 60° V-thread cut into a shank: a triangular tooth profile
# pointing radially INWARD (negative local-x), swept at the shank's major
# radius and differenced out. See `lib.standard.fasteners.cap_screw`'s
# `threads="real"` for the full worked version (tooth depth ≈0.6134×pitch).
cad.with_sketch("xy")
apex = cad.point2d(-0.6, 0.0)
top = cad.point2d(0.0, 0.35)
bot = cad.point2d(0.0, -0.35)
tooth = region(loop=[cad.line2d(apex, top), cad.line2d(top, bot), cad.line2d(bot, apex)],
              inside=(-0.2, 0.0))
tpath = cad.helix(radius=3.0, pitch=1.0, turns=12, axis_origin=(0, 0, -12))
tool = cad.sweep("xy", tooth, tpath, quality="high", export=False)
shank = cad.bool_difference(shank, tool, quality="high")

```

A real thread/groove is sub-cell at coarse dual-contouring resolutions — an
M3 tooth (depth ~0.3 mm) needs `quality="high"`/`"ultra"` to render at all.

(See `archive/docs-2026-08-23/ArchitectureNotes-Sweep.md` §0.) `lib.standard.fasteners.cap_screw`
forces this automatically for `threads="real"`.


**Planar rails: `cad.path(plane, chain, name=None)`.** An **open** directed
word of sketch elements on `plane`: lines/arcs/splines chained end-to-end,
e.g. `chain=[l1, rev(a2), s3]` — `rev(...)` traverses an element against its
intrinsic orientation, exactly as in `region(loop=...)`. Unlike
`region(loop=...)` the chain does **not** close, and a closed element (a full
circle/ellipse, or a closed spline) cannot appear in it. **Authoring trap:
keep the rail AWAY from the profile region's elements** — the profile anchors
to the sketch origin and the rail's position is independent of it, but a rail
element passing through the profile's boundary splits the profile's detected
region and silently changes the swept section.


```python
# A channel: a circle profile swept along a line→arc→line rail.
cad.with_sketch("xy")
origin = cad.point2d(0, 0)
wire = cad.circle2d(origin, 1.5)                 # profile AT THE SKETCH ORIGIN
r1 = region(loop=[wire], inside=(0, 0))
# rail elements drawn well away from the profile:
q1 = cad.point2d(10, 0)
q2 = cad.point2d(30, 0)
q3 = cad.point2d(40, 10)
q4 = cad.point2d(40, 30)
ac = cad.point2d(30, 10)                         # arc center
l1 = cad.line2d(q1, q2)
a2 = cad.arc2d(ac, q2, q3)
l3 = cad.line2d(q3, q4)
rail = cad.path("xy", chain=[l1, a2, l3])
channel = cad.sweep("xy", r1, rail)
```


**3D rails: `cad.path3d(points, closed=False, up=None, name=None)`.** A 3D
free-curve rail through **named 3D point refs** — `cad.point(x, y, z)` results
(or any other named 3D point), **NOT raw `(x, y, z)` tuples**. A non-uniform
(chordal) Catmull-Rom curve is fit through the points, then framed with a
rotation-minimizing frame (RMF) so the swept section doesn't spuriously twist
along a curving, non-planar rail. `up=(x, y, z)` optionally seeds the
section's start orientation (e.g. a rectangular tube's flat), re-orthogonalized
against the path's first tangent; the default is a deterministic
auto-perpendicular direction. `closed=True` is **not yet supported** — it
raises a clear error.


```python
# A cable run through three points:
p1 = cad.point(0, 0, 0)
p2 = cad.point(10, 5, 3)
p3 = cad.point(20, 0, 8)
rail = cad.path3d(points=[p1, p2, p3])
cad.with_sketch("xy")
origin = cad.point2d(0, 0)
wire = cad.circle2d(origin, 0.5)
cable = cad.sweep("xy", region(loop=[wire]), rail)
```


**Section-varying sweeps: `cad.sweep(..., sections=[...])`.** Instead of one
`plane=`/`region=` profile, pass a list of keyframes the profile morphs
between, keyed by arc-length fraction along the path:

```python
sections=[sweep_section(fraction=0.0, plane="xy", region=region(loop=[big])),
          sweep_section(fraction=1.0, plane="zx", region=region(loop=[small]))]
```

- `sections=` and the single `plane=`/`region=` form are **mutually
  exclusive** — passing both, or neither, raises `ValueError`.
- `sections` needs **≥ 2** entries; fractions must be **strictly increasing**,
  with the first **exactly `0.0`** and the last **exactly `1.0`**.
- Holes are **NOT supported** in this form (a single-`region=` sweep keeps
  full hole support).

- **Do not conflate:** the top-level `sweep_section(fraction, plane, region)`
  helper here is a **sweep-profile keyframe**. `cad.section(body, plane)` in
  §6.9 is a DIFFERENT, unrelated op — an **analysis cross-section curve** of
  an existing body.


```python
# A taper: big circle -> small circle along a straight rail.
p1 = cad.point(0, 0, 0)
p2 = cad.point(0, 0, 20)
rail = cad.path3d(points=[p1, p2])
cad.with_sketch("xy")
origin = cad.point2d(0, 0)
big = cad.circle2d(origin, 5)
cad.with_sketch("zx")
origin2 = cad.point2d(0, 0)
small = cad.circle2d(origin2, 1)
taper = cad.sweep(path=rail, sections=[
    sweep_section(fraction=0.0, plane="xy", region=region(loop=[big])),
    sweep_section(fraction=1.0, plane="zx", region=region(loop=[small])),
])
```

The two sections above deliberately live on **different planes** (`"xy"` and
`"zx"`) even though both circles sit at their own sketch's origin — two
same-origin profiles that differ only in size, drawn on the SAME plane, are
indistinguishable from a single annular region: area detection nests the
smaller inside the larger as a **hole** instead of seeing two separate
sections. Put same-origin sections on different planes.

### 6.5 Booleans (variadic; keep-result, consume inputs)

```python
u = cad.bool_union(a, b)            # or more: bool_union(a, b, c, ...)
d = cad.bool_difference(box, tool)  # first minus the rest
i = cad.bool_intersection(a, b)

# Blended seams:
cad.bool_union(a, b, blend="smooth", radius=2)     # rounded fillet at the seam
cad.bool_difference(a, b, blend="chamfer", radius=2)  # flat 45° bevel
```

**Only VISIBLE bodies are exported**: a boolean's consumed operands drop out of
the file on their own, and `cad.hide(x)` removes a body until `cad.show(x)`.

**The argument rules are enforced, and the blended form is stricter than the
plain one.** All three booleans need **at least two** bodies. A `blend=` requires
**exactly two** — `cad.bool_union(a, b, c, blend="smooth", radius=2)` is a natural
extrapolation from the variadic plain form and it raises. A `blend=` also requires
a `radius`, and that radius must be **greater than zero**; a `radius=` passed
without a blend that uses one raises as well, rather than being quietly ignored.

`blend=` accepts three values: `"smooth"`, `"chamfer"`, and `"sharp"`. `"sharp"`
is the explicit spelling of the default — it takes no radius (passing one raises)
and behaves exactly as omitting `blend=` does. Any other value raises an error
naming the legal set.

**A caveat for a SHARP boolean over a blended operand.** A `bool_difference`/
`bool_intersection` whose sharp result cuts through an operand that is itself
a `blend="smooth"`/`blend="chamfer"` result (or an offset) routes through a
CPU-only adaptive mesher, not the usual GPU-sampled grid — GPU-sampled initial
values are prohibitively slow for this shape class (measured 2.5 → 28
minutes). That mesher's base grid is capped at a fixed resolution
(192 cells/axis) regardless of `quality=` — once a body's true cell demand
materially exceeds that cap, raising `quality=` (§9) or calling
`set_cell_size` (§7) does not refine this body any further; a mesh that hit
the cap logs a diagnostic saying so.

### 6.6 Offset / shell

```python
big = cad.offset(box,  2)    # grow outward in every direction
small = cad.offset(box, -2)  # shrink inward
shell = cad.bool_difference(big, small)   # hollow shell
```

### 6.7 Body transforms (keep-both: source stays, a NEW body is returned)

```python
b2 = cad.move(b, translate=(10, 0, 0))
b3 = cad.rotate(b, axis=(0, 0, 1), angle=45, center=(0, 0, 0))
b4 = cad.scale(b, factor=2)                 # or sx=/sy=/sz= for per-axis
b5 = cad.mirror_body(b, plane="yz")
b6 = cad.copy(b)
cad.delete_body(b)                          # delete (cascades to consumers)
```


### 6.7b Patterns (one line, N-1 new bodies)


A pattern is ONE editable script line that produces `count - 1` copies of a
seed body. Change `count`, `spacing` or `angle` on that single line and the
whole array follows — unlike a hand-written loop of `cad.move(...)` calls,
which spreads the same idea over N lines.

```python
row = cad.pattern_linear(peg, direction=(1, 0, 0), count=4, spacing=10, name="row")
ring = cad.pattern_circular(bolt, axis=(0, 0, 1), count=6, angle=360, name="ring")
fan = cad.pattern_circular(blade, axis=(0, 0, 1), count=3, angle=90, center=(20, 0, 0), name="fan")
```

- **`count` includes the seed.** `count=4` gives the seed plus 3 copies (at 10,
  20 and 30 mm above). It must be 2…1000; for more, write a python loop.
- **`direction` is normalized** — only its direction matters; neighbours are
  always `spacing` mm apart. `spacing` may be negative (patterns backwards).
- **`angle` is the TOTAL sweep**, not a per-copy step, and must satisfy
  `0 < |angle| <= 360`. A FULL circle (exactly ±360) steps by `angle / count`
  so the last copy stops one step short of the seed; any partial fan steps by
  `angle / (count - 1)` so a copy sits at each end (`angle=90, count=3` puts
  copies at 45° and 90°). Negative sweeps go the other way.
- **The copies are named `<name>_1`, `<name>_2`, …**, where `<name>` is the
  variable you assign to, or an explicit `name=` — one of the two is REQUIRED.
  They are injected as bare names too, so `cad.hide(row_2)` works. The return
  value is `[seed, copy_1, …]`, seed first, `count` entries long.
- If the assignment target sits inside a loop, or the same variable is
  assigned more than once in the file, `<name>` itself gets numbered too
  (`row_1`) and the copies become `row_1_1`, `row_1_2`, …; a hand-written name
  that collides with a pattern's copy range is refused if it comes first in
  the script and silently renumbered if it comes second — prefer distinct
  names.
- **Copies are ordinary bodies**: colour, hide, export and cell-size all work
  per copy (`cad.set_color(row[2], "red")`, `cad.set_export("row_1", False)`).
  They are NOT editable one-by-one in the Body Inspector's Quality picker —
  they have no creation line of their own (the same limitation the per-glyph
  bodies of `cad.text(..., distance=...)` have). Edit the pattern line instead,
  or use `cad.set_cell_size(...)`.
- If a name like `row_1` is already taken, the pattern is refused with a
  message naming the clash — pick a different pattern name.

### 6.8 Topology points & custom planes

After an extrude/revolve, the body exposes its **far-face vertices** as
attributes, which you can use as 3D defining points for a custom sketch plane:

```python
box = cad.extrude("xy", rect_region, 20)
plane = cad.create_sketch_plane(box.v0, box.v1, box.v2, name="topface")  # oblique plane
cad.with_sketch("topface")
# ... draw on the new plane, e.g. a circle, then extrude/loft from it ...
```

Always pass `name=` — that name IS the plane's identity for everything that
comes later (`cad.with_sketch("topface")`, `cad.extrude("topface", …)`,
`cad.loft(start_plane="topface", …)`), and it is what the app writes when you
create a plane in the GUI. Omitting it leaves python to auto-name the plane
`custom1`, `custom2`, … in creation order, so inserting one earlier plane
renumbers every later reference.

Vertex names follow `body.v0, body.v1, ...` (holes: `body.h0_v0`; symmetric
extrudes split into `body.pos_v0` / `body.neg_v0`). The exact set depends on the
body — when unsure, prefer building reference geometry with `cad.point(x,y,z)`
and `create_sketch_plane`.


### 6.8b Body refs: bare vs quoted


Two spellings address a body, and which one is correct depends on what the call
does with it:

- **Value-producing operations take the bare ref** — the python variable the
  body was assigned to: `cad.bool_union(b1, b2)`, `cad.move(b, translate=…)`, `cad.section(b, "yz")`, `cad.component_export(b)`.
  A string will not do here.
- **Post-hoc property setters accept EITHER** — a `BodyRef`/`Ref` or the body's
  name as a string. `cad.set_color`, `cad.set_export`, `cad.set_cell_size`,
  `cad.hide` and `cad.show` all take both forms, and each also exists as a
  chainable `BodyRef` method except `hide`/`show`.

**Prefer the string form for property setters**, even when a variable is in
scope. The reason is that a property setter must also be able to address bodies
that have **no python variable at all** — the parts inside a `cad.instance(...)` of a component, and bodies created
inside a `for` loop where the variable has
since been rebound. A bare identifier in those positions is a `NameError` on the
next replay, whereas a string literal is legal python for every body. The string
form is also what the app writes, so a GUI-authored document and a hand-written
one agree:

```python
cad.set_color("body1", "#FF0000")          # always valid
cad.set_color(plate, "#FF0000")            # valid while `plate` is still bound
cad.set_export("motor_1_can", False)       # an instance part — no variable exists
```


### 6.9 Analysis (snapshots, refreshed on full re-run)

```python
s = cad.section(body, "yz")        # cross-section curve at a plane
sp = cad.project(body, "yz")       # silhouette projection onto a plane
pp = cad.project_point(box.v0, "zx")
```

Both emit TRUE circles/arcs/lines when the body is analytic for the request —
extrudes (including booleans, transforms and component instances of them)
sectioned/viewed along their extrusion axis. Projection then includes every
profile edge (holes, bosses — a drawing-style view). Other bodies/orientations
fall back to a sampled spline.


---

## 7. Appearance, quality & visibility

Colors are display-only; they do not affect geometry. Set on any body:

```python
cad.set_color(body, "#C62828", finish="glossy")    # hex
cad.set_color(body, "red")                          # named color (defaults to glossy)
cad.extrude("xy", r, 10).set_color((0.2, 0.4, 1.0), finish="metallic")  # chainable, RGB tuple
```

**Body-name strings:** `set_color`, `set_cell_size`, `set_export`, `hide` and
`show` all accept EITHER a `BodyRef`/`Ref` OR a **body-name string** as the
body argument — e.g. a component instance part (`<instance>_<part>`, see §8.1)
that has no python variable of its own.

- Color: `"#RRGGBB"`, `"#RRGGBBAA"` (alpha = translucency), `"#RGB"`, a name
  (`red`, `blue`, `steel`, `gold`, …), or an `(r, g, b[, a])` tuple (0–1 or 0–255).
- `finish`: `"matte"`, `"glossy"`, `"metallic"`, `"glass"` (glass is translucent).
- Colors are written into the 3MF export as base-material colors, and into
  glTF/GLB export as a PBR material per body — the finish becomes the
  metallic/roughness factors, and glass (or any alpha below 1) blends.
- Colors set **inside a component** propagate to every instance of it.

### Document mesh quality: `set_quality`

> **A generated script should not contain this call at all — see §C.** This
> section documents it for the case where you are *editing* a document that
> already has one, or where the user has explicitly asked for a fixed quality.

The five tiers, in order, are:

| Tier | Cell size | Budget (cells/axis) | Notes |
|---|---|---|---|
| `"preview"` | 2.0 mm | 64 | fast and coarse; good while iterating |
| `"standard"` | 0.5 mm | 128 | **the default when nothing is set** |
| `"high"` | 0.25 mm | 200 | |
| `"ultra"` | 0.1 mm | 256 | |
| `"precision"` | 0.1 mm **floor** | 1289 **requested** | see the caveats below |

`quality=` on an individual body op is a one-off override; `cad.set_quality(...)`
sets the **document-wide default** every body without its own `quality=` falls
back to (same five values):

```python
from flywheelcad import *
cad = FlywheelCAD()
cad.set_quality("high")   # must come before the first body-creating command

body1 = cad.extrude("xy", region, 10)   # meshes (and tessellates its curves) at "high"
body2 = cad.extrude("xy", region2, 5, quality="ultra")   # per-body override still wins
```

- **Must appear before the first body-creating command anywhere in the
  script** (extrude, revolve, loft, multi_loft, sweep,
  bool_union/difference/intersection, offset, move/rotate/scale/mirror_body/copy,
  instance, text) — refused otherwise, **including a body created inside a
  `with cad.component(...)` block**: a component that is never instanced
  builds straight into the document, and even an instanced component's
  sub-design is built with whatever quality is active *at the moment its
  block opens* — a `set_quality(...)` after the block, even before any
  top-level body, can never reach it. This is not a style preference: the
  quality is baked into a body's curve tessellation *at the moment the body
  is created*, so a `set_quality(...)` line after a body would change that
  body's mesh resolution but not its curve resolution, a half-applied state.
- A script may call it **at most once**, and **not inside a
  `with cad.component(...)` block** — components inherit the assembly's
  quality automatically; a `set_quality(...)` line inside one is refused with
  a "document-scoped setting" error.
- Put `cad.set_quality(...)` **before** any `with cad.component(...)` block if
  you want it applied to that component's bodies too.
- An unrecognized value is a hard error, never a silent fallback — the message
  names the five legal values. Values are case-sensitive: `"High"` is refused.
- **`"precision"` is the 1289-cell-budget tier** ("Precision" in the UI),
  accepted since 2026-07-29 — earlier builds REFUSE a document that sets it.
  Three properties make it unlike the other four:
  - **The budget is a request, not a promise.** A large body is measured against
    the device's memory first and given the largest lattice up to 1289 that this
    machine can actually serve; if even the fitted budget does not fit, the
    quality ladder steps down (precision → ultra → high → standard → preview).
    The body is geometrically correct at every step — what changes is resolution.
  - **Its 0.1 mm cell size is a FLOOR, not a target.** Precision is therefore
    *identical to ultra* for any body small enough that ultra already achieves
    0.1 mm cells. It differs only where the budget binds, i.e. on large parts —
    roughly above 13 cm of extent. Applying it to small parts costs time and buys
    nothing at all.
  - **It is expensive in measured, not theoretical, terms.** Precision bodies
    mesh one at a time; a 15 mm control horn once took 863 s at the old 1024³
    budget, and a shipped sample spent 114 minutes, most of it on parts too small
    to benefit. Each retained precision mesh is on the order of 900 MiB and lives
    as long as the document is open.

  Prefer a per-body `quality="precision"` on the one body that needs it over a
  document-wide setting.
- A headless render's `--quality` flag overrides this document setting.
- **It is a document setting, not a component one.** `cad.set_quality(...)`
  only takes effect when it runs as the DOCUMENT itself — i.e. the file is
  the one actually being executed (`__name__ == "__main__"`), same as
  double-clicking Run on it. A `set_quality(...)` line inside a component
  module has **no effect when that module is imported** by an assembly (it
  is silently ignored, with a warning on stderr): every `FlywheelCAD()` in
  one process shares one command stream, so a naive component-side call
  would otherwise leak into whichever document imports it. Don't write
  `cad.set_quality(...)` in a component file expecting it to affect
  assemblies that import it — write it in the assembly instead. The
  importing document's own quality already reaches the component's bodies
  automatically (components inherit the assembly's quality); the
  component's `set_quality(...)` still applies when that file is opened
  and run standalone.

### Document presentation unit: `set_units`

> **A generated script should not contain this call at all — see §C.** This
> section documents it for the case where you are *editing* a document that
> already has one, or where the user has explicitly asked for a fixed unit.

`cad.set_units(units)` sets the document's presentation unit — `"mm"`, `"cm"`,
or `"in"` — for GUI entry/readout conversion and 3MF export ONLY:

```python
cad.set_units("in")
```

- **Geometry, this script's own numeric literals, the solver and every cache
  stay millimetres regardless of this call.** A `set_units("in")` document
  still authors `cad.extrude("xy", region, 10)` for a 10 MM extrude — the
  document unit never changes what a script's own numbers mean.
- **No ordering requirement at all**, unlike `set_quality`: nothing reads the
  document unit at command time, so the line may sit anywhere relative to
  body-creating commands, including after one.
- A script may call it **at most once**, and **not inside a
  `with cad.component(...)` block** — components inherit the assembly's unit
  automatically, mirroring `set_quality`'s identical rule.
- An unrecognized value is a hard error, never a silent fallback to `"mm"`.
  Values are case-sensitive.
- **It is a document setting, not a component one**, honouring the same
  `__name__ == "__main__"` distinction as `set_quality`: a `set_units(...)`
  line inside an imported component module has no effect on the importing
  assembly (a warning prints to stderr); the component's own line still
  applies when that file is opened and run standalone.
- Absence means `"mm"` — the same "absence is the stated default" convention
  as mesh quality; nothing needs to be written to get millimetres.
- Affects the exported `<model unit="…">` attribute and every vertex
  coordinate in `.3mf` output. STL and OBJ export stay millimetres always,
  regardless of this setting; glTF/GLB export is always METRES
  (millimetres × 0.001) and +Y-up, regardless of this setting.

### Document default cell size: `set_default_cell_size`

> **A generated script should not contain this call at all — see §C.** This
> section documents it for the case where you are *editing* a document that
> already has one, or where the user has explicitly asked for a fixed
> document-wide cell size.

`cad.set_default_cell_size(cell_size)` sets the dual-contouring cell size, in
millimetres, for every body that does not set its own:

```python
cad.set_default_cell_size(0.2)
```

- **The precedence ladder**, most specific first: a per-body
  `cad.set_cell_size(body, size)` beats this; this beats the machine-local
  precision floor in Settings; that beats the quality tier's own cell size.
- **It raises every body's cell budget**, exactly as a per-body
  `set_cell_size` does — otherwise a fine value would be silently coarsened
  straight back by the tier's budget. That is what makes it a whole-document
  resolution commitment in the same class as a document-wide `"ultra"`: cost
  scales with the number of bodies, not with the one you were thinking about.
  The console warns per body where the budget still clamps the request.
- **Ordering matters**, like `set_quality` and unlike `set_units`: a swept body
  bakes its path density from this value when the sweep command RUNS, so the
  line must appear **before the first body-creating command**. A script may
  call it **at most once**, and **not inside a `with cad.component(...)`
  block** — components inherit the assembly's default automatically.
- **A value below `1e-6` mm (one nanometre) is an error**, as are zero,
  negative and non-finite values — never a silent clamp. The same message the
  app's own sheet shows.
- **It is a document setting, not a component one**, honouring the same
  `__name__ == "__main__"` distinction as `set_quality`.
- A headless render's `--quality` flag overrides this document setting, exactly
  as it overrides `cad.set_quality(...)`.
- Absence means "let the quality tier decide" — nothing needs to be written to
  get the tier's own cell size.
- Applies to sampled (DC) meshing; exactly-meshed plain extrudes/revolves are
  unaffected. Note that a plain extrude's cached 2D profile does not scale with
  this value.

### Mesh resolution: `set_cell_size`

Sampled meshing (booleans, offsets, lofts, rounded/drafted extrudes) uses a
quality tier whose cell budget is RELATIVE to the body's size — a large body
gets large cells, so small features (grooves, pockets, thin rods) can lose
detail even at `quality="ultra"`. Give such a body an ABSOLUTE cell size in
model units:

```python
wing = cad.bool_difference(skin, groove, bay)
cad.set_cell_size(wing, 0.8)      # 0.8-unit cells regardless of body size
wing.set_cell_size(0.8)           # chainable form
```

Clamped to a hard total-cell cap (the console warns when the clamp engages).
Exactly-meshed plain extrudes/revolves ignore it (they are already exact).
The body argument may also be a body-name string (see the shared note at the
top of §7).

**Minimum value: `1e-6` mm — one nanometre.** Anything smaller is refused with a
message naming the minimum and suggesting a typo'd exponent, and a zero or
negative value is refused earlier still. This exists because a sub-nanometre cell
used to crash the mesher outright.

**Write one line per body, with a bare once-bound identifier or a string
literal.** A `set_cell_size` line whose body argument arrives through a loop
variable, an alias, an expression, or a name that is rebound elsewhere cannot be
attributed to a body by the Body Inspector — and a single unattributable line
blocks *clearing* the cell size for every body in the document. `for w in wings:
cad.set_cell_size(w, 0.8)` is the pattern to avoid. See §C for the full reasoning.

**Combining it with a quality tier.** A body may carry both. The explicit cell
size wins for the cell size; the total-cell budget becomes the LARGER of the
two, so setting a cell size never *lowers* the ceiling the quality tier already
granted. (Before this rule it did — a `set_cell_size` call on a high tier
silently dropped the body to the override's own budget.)

**Exception: the adaptive-boolean path (§6.5).** A sharp `bool_difference`/
`bool_intersection` over a smooth/chamfer-blended (or offset) operand meshes
on a CPU-only adaptive mesher with its own fixed 192-cells/axis cap;
`set_cell_size`, like `quality=`, cannot raise that body's resolution past it
once the cap materially binds.

### Visibility: hide/show

```python
cad.hide(body)                    # hide one or more bodies from the 3D view
cad.hide(scaffold_a, "tail_i_fin")   # variadic; refs and name strings mix
cad.show(body)                    # re-show previously hidden bodies
```

- Visibility **persists across save/reopen** — it is script truth, not a
  view-only toggle.
- A hidden body is **excluded from the export** (3MF/STL/OBJ/glTF, GUI and CLI
  alike) until it is shown again — the same rule the boolean's automatically
  hidden operands ride on, so only the final body ships. The headless CLI's
  count line says how many bodies it left out; a SELECTED-bodies export still
  ships exactly what was selected, hidden rows included.
- Each argument is a `BodyRef`/`Ref` or a body-name string (shared note at the
  top of §7).
- `cad.hide(...)` expresses an **EXPLICIT hide only**: a boolean automatically
  hides the operands it consumes, so those do not need — and must not get —
  their own `cad.hide(...)` line.
- `cad.show(operand)` placed AFTER a boolean line re-reveals an operand the
  boolean consumed: later script position wins.
- There is **no chainable `body.hide()`/`body.show()` method** — unlike
  `set_color`/`set_export`/`set_cell_size`, which exist both as `cad.`
  free functions taking the body and as `BodyRef` methods, visibility is
  free-function only.
- Calling `cad.hide()`/`cad.show()` with zero arguments raises `ValueError`.

### Export flag: set_export

```python
cad.set_export(body, False)       # exclude an existing body from export (every format)
body.set_export(True)             # chainable form; value=True is the default
cad.set_export("motor_1_can", False)   # body-name string form
```

The **post-hoc** toggle, versus the CREATION-time `export=False` kwarg (§6
intro, §8.3's `cad.instance(..., export=False)`): `set_export` flips the flag
on any body or instance part that already exists, including ones with no
python variable (shared body-name-string note at the top of §7).

`value` must be a real `bool`. Anything else (a string, `0`/`1`, `None`)
raises `ValueError` — pass a real `bool`.

The flag applies to **visible** bodies: it picks which of them to leave out of
the file. It does not put a HIDDEN body back into the export —
`cad.set_export(x, True)` on a hidden body raises nothing and is remembered,
but takes effect only once `cad.show(x)` makes the body visible again.

---

## 8. Components & assemblies

Use components to define a reusable part once and place it many times. Components
are defined **flat** (never nest `with` blocks) and nested **by reference**.

### 8.1 Define a component

```python
with cad.component("bracket"):
    cad.with_sketch("xy")
    # ... sketch + region ...
    body = cad.extrude("xy", r, 5)
    cad.set_color(body, "steel", finish="metallic")
    cad.component_export(body)                      # assembly-visible result
    cad.component_export_point("hole", cad.point(10, 0, 0))   # named anchor for mating
```

- `cad.component_export(body, name="friendly")` marks a body as a visible part of the
  component. A multi-body component exports several; each surfaces on an instance
  as `<instance>_<name>`.
- `cad.component_export_point("anchor", point)` promotes a reference point; each instance
  exposes it as `<instance>.<anchor>` (e.g. `b1.hole`), usable in assembly
  geometry, mates, and as a target for other parts.
- A component that is **never instanced** in a run is *transparent*: it builds the
  top-level design. So a component file run directly behaves like a normal part.
- `cad.component(name, label=None)` takes an optional **`label=`** — a
  human-friendly display name surfaced in the app's UI, free of the
  identifier-safety constraints the `name` carries. Use it when the generated
  component name is machine-shaped (`wing_span46_chord18`) but the user should
  see something readable ("Wing — 46 mm span").

### 8.2 Parametric components

Build a distinct component per parameter set, memoized by parameters:

```python
def make_wing(span, chord):
    def build():
        cad.with_sketch("xy")
        # ... use span/chord ...
        cad.component_export(skin)
    return cad.parametric("wing", build, span=span, chord=chord)

WING = make_wing(span=46, chord=18)   # returns a component name
```

Helpers: `cad.component_name(prefix, *parts)` builds the deterministic,
identifier-safe name `parametric` memoizes on (same parameters → same name);
`cad.has_component(name)` reports whether that component was already emitted
this run.

`cad.parametric(prefix, build, *, label=None, **params)` also accepts a
**`label=`** display name. Three non-obvious rules govern it: it is
**keyword-only**, it is **never passed through to `build`** (so your build
function does not need to accept it), and it **does not contribute to the
memoization key** — two calls differing only in `label` return the *same*
component, and the first label wins.

### 8.3 Instance & place

```python
b1 = cad.instance("bracket")                          # at the origin
b2 = cad.instance("bracket", translate=(50, 0, 0))    # placed
b3 = cad.instance("bracket", mirror_plane="zx")       # mirrored
b4 = cad.instance(WING, scale=2, angle=10, axis=(0,0,1))  # transforms compose
b5 = cad.instance("arm", axis=(0,0,1), angle=30, center=(20, 0, 0))  # pivot
jig = cad.instance("jig", export=False)   # excluded from mesh export
```

An instance ref is usable anywhere a body is (booleans, transforms, `set_color`).

- **`center=`** is the pivot the rotation turns about. It is consumed only when
  `axis=`/`angle=` are also given; on its own it does nothing.
- **`quality=` is accepted and then silently dropped**, with a warning on stderr
  that the host mirrors into its log. A per-instance quality has no persisted
  home, so a placed part inherits its quality from the component definition.
  Do not pass it and expect an effect — set the quality inside the component, or
  leave it to the document (§C).
- An unknown kwarg raises `TypeError` rather than being ignored.

### 8.4 Mates (position instances relative to each other)

```python
# Closed-form snap: instance's anchor coincides with a target point (+offset):
cad.mate_coincident(b2, "hole", b1.hole, offset=(0, 0, 5))

# Snap + orient: b2 moves (t1/t2 are fixed) so its "a1" anchor coincides
# with t1 (+offset), and the a1->a2 direction on b2 is rotated to become
# parallel to the t1->t2 direction:
cad.mate_align(b2, "a1", "a2", t1, t2, offset=(0, 0, 0))

# Solved 6-DOF pose: several mate() on one instance are solved together
# (e.g. three point mates fully fix position AND orientation):
cad.mate(b2, "p0", target0)
cad.mate(b2, "p1", target1)
cad.mate(b2, "p2", target2)

# Solved AXIS mate: the b2 axis "a1"->"a2" is held COLLINEAR with the
# assembly axis t1->t2. Unlike mate_align it does NOT also drop a1 onto t1 —
# b2 stays free to slide along the shared axis and spin about it, which is
# what a rail, a shaft or a bolt wants. Composes with mate() in one solve:
cad.mate_axis(b2, "a1", "a2", t1, t2)
cad.mate(b2, "a1", point_on_that_axis)   # optional: pins the slide too
```

A solved mate's **target is a reference the solver never moves** — the instance
is pulled onto the target, never the target onto the instance (so a free
`cad.point2d` target stays exactly where your sketch put it). `cad.mate` and
`cad.mate_axis` take no `offset=`; the snaps do.

`cad.mate_axis` leaves two real degrees of freedom open. If nothing else
constrains them, the along-axis position and the roll angle come out of the
solver's minimum-perturbation bias — deterministic for a given script, but an
artefact of the seed pose rather than something to design around. Add a
`cad.mate` onto a point that lies **on** the target axis to pin the slide (the
two mates then agree; a point mate onto a target **off** the axis
over-constrains the pose and the solver reports a miss).

**Mate rules the run enforces.** These are checked on every run, before the
assembly solve, and a violation **fails the run** with a named error (rather
than converging to a silently wrong pose, which is what they used to do). The
GUI refuses the same shapes up front, with the same wording.

| Refused | Why |
|---|---|
| `cad.mate` on an instance placed with `rotate=`/`mirror_plane=`/non-unit `scale=` | the solve rebuilds a pure rigid `R\|t` with rotation seeded at identity, so the placement is silently discarded |
| `cad.mate` **and** `cad.mate_coincident`/`cad.mate_align` on the same instance | the solve re-poses the instance *after* the snap ran, silently discarding the snap |
| `cad.mate` onto an anchor of an instance that is itself solved-mated (a **chain**, in either order) | the mate captures the target's *pre-solve* position and keeps it forever — the part lands where its target used to be |
| `cad.mate_coincident`/`cad.mate_align` onto an anchor of a solved-mated instance | the snap runs against the target's pre-solve pose, and the solve then moves the target away |
| `cad.mate` onto an instance's own anchor | degenerate: it chases a target driven by the very DOFs it drives |
| `cad.mate` inside a `with cad.component(...)` block | solved mates are **assembly-scoped**: the solve only sweeps top-level instances, so it would never solve. Use a snap mate inside the component, or mate the component's *instance* in the assembly |
| `cad.mate_axis` whose two anchors are the same component-space point | a zero-length axis has no direction to hold |

`cad.mate_axis` obeys every `cad.mate` row above as well (it grants the same
placement DOFs). One case is a **warning** rather than a refusal: if the two
*targets* collapse onto one point — reachable by editing geometry far away —
the run names that mate, skips it for that run, and leaves everything else
solved.

Two identical `cad.mate` lines are a **warning**, not an error: the duplicate is
dropped before the solve and the geometry is unaffected.

Mating onto an anchor of an instance that has **no** solved mate is always fine —
that is what every shipped sample does (`cad.mate_coincident(arm, "hub",
servo_inst.spline_tip)`).

### 8.5 Nesting & multi-file projects

- Components nest by **instancing** other components inside a `with cad.component`
  block, then re-exporting the instance: `panel = cad.instance(WING); cad.component_export(panel)`.
- Larger projects split components into sibling `.py` files imported by an
  assembly file. The folder is on the import path, so `import fuselage` resolves a
  sibling `fuselage.py`. Each component file defines (and may instance) its part.
  See `Samples/AirplaneNested.fwcad/` for a two-level assembly.

### 8.6 Component libraries (vendored parts)

Reusable catalog parts (motors, bearings, fasteners) come from **component
libraries** — folders of ordinary Python modules. The **standard library** ships
inside the app; users can add custom library folders. Documents consume library
parts **copy-on-use**: the module is copied ("vendored") into the document
folder under `lib/<library>/`, so every document stays self-contained and old
designs never change when a library updates.

```
MyRobot.fwcad/
  main.py                   # the document's script (§A)
  bracket.py                # user components (siblings)
  lib/
    standard/steppers.py    # vendored library modules — imported, don't edit
```

This is the strongest argument for the bundle format in §A: `lib/` is *inside*
the document, so the vendored parts travel with it. In a flat `.py` project the
same `lib/` sits in the enclosing folder, shared with every other script beside
it — and copying the `.py` alone leaves the motor behind.

The canonical import line carries the provenance:

```python
from lib.standard.steppers import stepper

m = stepper(cad, size=17, length=48)        # -> component name (parametric)
motor = cad.instance(m, translate=(80, 0, 20))
cad.mate_coincident("bracket_1", "hole_0", "motor.bolt_0")
```

Library factories take `cad` as the first argument, return a component name for
`cad.instance(...)`, and export a **documented anchor contract** so parts can be
mated without reading their source. Treat files under `lib/` as read-only: they
carry a provenance header (`# flywheelcad-library: <library>/<module> <version>`)
and are refreshed wholesale by the update flow. To fork one, copy it up into the
document folder as a user component instead.

When AUTHORING a library module: reference sibling modules of the same library
with **relative imports** (`from .fasteners import bolt` / `from . import
shafts`) — those resolve both in the library folder and after vendoring, and
the copy-on-use step follows them so dependencies vendor together. Declare
`__library_version__ = "x.y"` at module top level. Factories are public
module-level functions whose first parameter is `cad`; parameter defaults and
the docstring's first line surface in the library browser.

**Standard library: `steppers`** (`from lib.standard.steppers import stepper`)

- `stepper(cad, size=17, length=None, shaft_length=None, body="square", quality=None)`
  — NEMA frame sizes 8, 11, 14, 17, 23, 34; defaults are typical catalog
  dimensions. `body="square"` is the classic end-bell frame with real bolt
  holes through the front bell, an inset lamination stack, shaft flat, and
  wire exit; `body="round"` is a cylindrical can behind a square flange.
- Orientation: mount face on the XY plane at z=0, shaft up +Z, can extends −Z.
- Anchors: `mount_face` (flange-face center), `shaft_tip`, `shaft_base`, and
  `bolt_0..3` (mounting square, CCW from (+x, +y)).

**Standard library: `servos`** (`from lib.standard.servos import servo, horn`)

- `servo(cad, size="standard", quality=None)` — hobby-servo case classes
  `"sub_micro"` (SG90), `"micro"` (MG90S), `"standard"` (S3003/HS-422 class),
  `"large"` (HS-805 class): case, mounting flange with screw holes, gear
  bosses, output spline. Orientation: flange UNDERSIDE on XY at z=0, case
  hanging −Z, spline up +Z offset toward +X. Anchors: `mount_0..N`,
  `spline_base`, `spline_tip`.
- `horn(cad, style="single", spline="standard", length=None, quality=None)` —
  control horns: `"single"`, `"double"`, `"cross"`, `"disc"`; spline classes
  `"micro"`/`"standard"`/`"large"`. Anchors: `hub` (mate onto a servo's
  `spline_tip`) and `tip` / `tip_0..N` / `rim_0..5` at the linkage holes.

**Standard library: `fasteners`** (`from lib.standard.fasteners import ...`)

- `cap_screw(cad, thread="M3", length=12)` (DIN 912), `hex_nut(cad, thread=)`
  (ISO 4032), `washer(cad, thread=)` (ISO 7089) — threads M2…M8. Screws point
  −Z with the under-head plane at z=0. Anchors: `under_head`/`head_top`/`tip`;
  nuts and washers: `bottom`/`top`. `cap_screw(..., threads="real")` (and
  `fasteners_more.grub_screw`/`threaded_rod`) cut an actual helical V-thread
  instead of a smooth shank — see §6.4.
- **Negative bodies for boolean cuts**: `clearance(cad, thread=, length=,
  head_pocket=False)` (ISO 273 medium fit + optional DIN 912 counterbore) and
  `tap(cad, thread=, length=)` (tap-drill volume). Place at the same transform
  as the screw with `export=False`, then `cad.bool_difference(part, cut)` —
  place a screw AND cut its hole in two lines.

**Standard library: `bearings`** (`from lib.standard.bearings import bearing`)

- `bearing(cad, designation="608", flanged=False)` — metric deep-groove sizes
  623/624/625/626/608/688/6000/6001/6800/6801/6900/6902; `flanged=True` adds
  the F-series locating flange at the z=0 face. Axis +Z. Anchors: `face_a`
  (z=0), `face_b`, `center`.

**Standard library: `extrusions`** (`from lib.standard.extrusions import rail`)

- `rail(cad, profile="2020", length=100)` — T-slot framing rails: 2020, 2040,
  4020, 2060, 3030, 3060, 4040, 4080. Profile on XY, extruded +Z. Anchors:
  `end_a`/`end_b` (profile centers) and `bore_a_i`/`bore_b_i` per cell center
  bore (tap for end joining).

**Standard library: `linkage`** (`from lib.standard.linkage import ...`)

- `ball_link(cad, thread="M2")`, `clevis(cad, thread="M2")` (M2/M3) — RC rod
  ends: shank along +Z from z=0, `pivot` anchor at the ball/pin center,
  `shank_end` at z=0. `pushrod(cad, diameter=2, length=80)` runs z 0→length
  with `end_a`/`end_b`. Mate pushrod ends to link shank_ends and link pivots
  to servo-horn tips.

---

## A ring of instances that follows its source

There is no "pattern instances" command, and none is needed. A mate reads its
target's position **live** — `InstanceMateConstraint` excludes the target from
its solver unknowns so the instance moves onto the target and never the reverse,
but re-reads the target's coordinates every iteration. Point the mates at
constraint-linked sketch points and the whole ring becomes parametric.

```python
step = cad.variable(90, driving=True)
hub = cad.point2d(0, 0)
seat0 = cad.point2d(40, 0, name="seat0")
l0 = cad.line2d(hub, seat0, construction=True)
for k, angle in enumerate(ring(4)):
    if k == 0:
        continue
    sk = cad.point2d(*polar(40, angle), name="seat%d" % k)
    lk = cad.line2d(hub, sk, construction=True)
    cad.equal_lines(line1=l0, line2=lk)
    cad.angle(line1=l0, line2=lk, angle=step * k)

for k in range(4):
    inst = cad.instance(peg)
    cad.mate(inst, "base", "seat%d" % k)
```

Drag `seat0` and every part follows, in the same solve. Edit `step` in the
variables panel and the ring re-fans — parts included — with no re-run. The
first half is the constraint-linked sketch pattern (see the manual's "Repeating
sketch geometry"); this only points mates at it.

**One mate pins POSITION, not orientation.** A coincident mate is three
residuals against the instance's six placement DOFs, so the copies all keep the
seed's orientation — a ring of parts that face the same way. To turn them with
the ring, export a second anchor and use `cad.mate_axis`.

**Assembly level only.** `executeSolvedMate` refuses a solved mate inside a
`with cad.component(...)` block, so this recipe places instances in the
assembly, not inside another component.

## 9. Quality & performance knobs

- `quality=` per body: `"preview"` (fast, coarse) → `"standard"` (the default) →
  `"high"` → `"ultra"` → `"precision"` (slowest, and only meaningfully different
  from `"ultra"` on large parts — §7). Use `"preview"` while iterating. **In a
  generated script, prefer to set none of these at all — §C.**
- An extrude/revolve with no `edge_radius` and no `draft` meshes EXACTLY (a
  twist still does; a boolean RESULT does not) — no cell grid exists, so
  `cad.set_cell_size` (§7) does nothing to it. There `quality=` controls the
  arc SAGITTA — chord error on circles — not a cell count.
- Prefer one `multi_loft` over many 2-section lofts + unions (no seams, fewer
  bodies). Note `multi_loft` is CPU-meshed and dominates build time at high
  quality.
- `edge_radius` and twisted/draft extrudes cost more to mesh.
- `cad.sweep` real threads/fine grooves need `quality="high"` or `"ultra"` —
  a coarse dual-contouring grid simply cannot resolve a sub-cell tooth (see
  §6.4); `bool_difference`-based thread cuts are also CPU-only (not
  GPU-packable), so they cost more than an equivalent plain extrude/revolve.
- A sharp `bool_difference`/`bool_intersection` over a `blend="smooth"`/
  `blend="chamfer"` (or offset) operand (§6.5) meshes on a CPU-only adaptive
  mesher capped at a fixed 192 cells/axis — past that cap, neither `quality=`
  nor `set_cell_size` (§7) increases this body's resolution further.

---

## 10. Pitfalls checklist (for generated scripts)


- [ ] Delivered as a `.fwcad` bundle — a directory whose `main.py` is the script
      (§A) — unless the user explicitly asked for a flat `.py`.


- [ ] `from flywheelcad import *` and `cad = FlywheelCAD()` at the top, at module
      level, with the handle bound to exactly the name `cad`, and every component `import` placed BELOW it.
- [ ] **No `cad.set_quality(...)` anywhere.** No blanket per-body `quality=`. No
      `cad.set_cell_size(...)` through a loop or an alias (§C).
- [ ] **No `cad.set_default_cell_size(...)` anywhere** (document-wide, app-managed);
      a per-body `cad.set_cell_size(body, size)` is the route for one finer body.
- [ ] **No `cad.set_units(...)` anywhere** — presentation-only, app-managed (§C).
- [ ] `cad.with_sketch(...)` set before each batch of 2D geometry; sketch axes and extrude direction taken from the §4.1 table (`"zx"` has u = −X).
- [ ] One profile per body where the shape allows (§3 rule 15): holes and slots as region holes, L/T/step outlines as the profile, round stacks as one revolve.
- [ ] Every element assigned to a unique, descriptive variable (names come from
      the LHS — don't shadow or reuse).
- [ ] Region `loop` is closed and **directed**; use `rev(...)` for reversed
      elements; include `inside=(x, y)` for any region with holes/ambiguity.
- [ ] Region `inside` and `point2d` use **sketch 2D coords**, not world coords.
- [ ] A closed loop drawn INSIDE a region's loop on the same sketch is REFUSED unless
      listed under `holes=`; the refusal names it and its remedies — declare it, draw
      the later profile on its own plane (`create_sketch_plane`), or put `inside=(x, y)`
      in it to keep it filled. Glyph counters under their own outline are the exception.
- [ ] `region(name=…)` is a label only; the body that consumes the region is what carries the script-addressable name.

- [ ] Place polygon vertices with `polar()` literals; don't constrain construction
      spokes with `angle`/`equal_lines` — `angle` is unsigned, so the polygon folds.

- [ ] Bodies built only after their region exists; booleans after their inputs; mates after their instances + exported anchors.
- [ ] Export only the final body — booleans hide their operands and hidden bodies are not exported;
      `cad.set_export(x, False)` is for VISIBLE bodies you do not want; a hidden body's export flag waits until it is shown.
- [ ] Over-span cutting/joining tools: start them below the face they enter and
      end them beyond the face they exit. A flush cap exports watertight now;
      over-spanning keeps the cut robust when a dimension later changes.
- [ ] Angles in degrees; `revolve` uses `angle=360` for a full solid.
- [ ] `cad.sweep` profiles are drawn CENTERED AT THE SKETCH ORIGIN — the coil
      radius / offset lives in the `cad.helix(...)` path, never both places.
- [ ] Transforms are keep-both — capture the returned new body; the source stays.

- [ ] Components defined flat; nest by instancing + re-exporting, never nested `with`.

- [ ] No randomness / time / external mutable state (re-execution must be stable).
- [ ] `cad.text(...)` strings are ordinary Python literals (escape quotes and
      backslashes the Python way); solid mode needs `distance > 0`, outline `None`.
- [ ] Don't rely on a spelling surviving a GUI re-save: the app's serializer emits
      ONE canonical spelling per command and OMITS default-valued kwargs (an
      in-place dimension edit replaces only the VALUE — §D.6). Both spellings run.


---

## 11. Complete worked examples

### 11.1 Parametric plate with a hole, extruded

```python
from flywheelcad import *
cad = FlywheelCAD()

W = cad.variable(40, driving=True)   # width
H = cad.variable(25, driving=True)   # height
T = 8                                # thickness

cad.with_sketch("xy")
p1 = cad.point2d(0, 0)
p2 = cad.point2d(40, 0)
p3 = cad.point2d(40, 25)
p4 = cad.point2d(0, 25)
l1 = cad.line2d(p1, p2)
l2 = cad.line2d(p2, p3)
l3 = cad.line2d(p3, p4)
l4 = cad.line2d(p4, p1)
cad.horizontal(line=l1); cad.horizontal(line=l3)
cad.vertical(line=l2);   cad.vertical(line=l4)
cad.length(line=l1, length=W);  cad.length(line=l2, length=H)   # driven by variables

center = cad.point2d(20, 12.5)
hole = cad.circle2d(center, 5)
cad.radius(circle=hole, radius=5)

plate_region = cad.region(loop=[l1, l2, l3, l4], holes=[[hole]], inside=(3, 3))
plate = cad.extrude("xy", plate_region, T, edge_radius=1)
cad.set_color(plate, "steel", finish="metallic")
```

### 11.2 Revolved cup + subtracted bore (booleans)

```python
from flywheelcad import *
cad = FlywheelCAD()

cad.with_sketch("xy")
# Closed rectangular profile (x = radius 0..20, y = height 0..40). The left edge
# l4 sits on x = 0 and doubles as the revolution axis. NOTE the loop is built
# from REAL lines — never put a construction element in a region loop (they are
# excluded from region detection). If you want a separate construction axis,
# offset the profile so it does not touch it (see test_extrude_revolve.py).
a = cad.point2d(0, 0)
b = cad.point2d(20, 0)
c = cad.point2d(20, 40)
d = cad.point2d(0, 40)
l1 = cad.line2d(a, b); l2 = cad.line2d(b, c); l3 = cad.line2d(c, d); l4 = cad.line2d(d, a)
profile = cad.region(loop=[l1, l2, l3, l4], inside=(5, 20))
solid = cad.revolve("xy", profile, l4, 360)     # axis_line = the left edge (x = 0)

# Hollow it: a smaller cylinder subtracted from the top.
cad.with_sketch("xy")
bore_center = cad.point2d(0, 0)
bore = cad.circle2d(bore_center, 16)
bore_solid = cad.extrude("xy", cad.region(loop=[bore], inside=(0, 0)), 36, offset=4)
cup = cad.bool_difference(solid, bore_solid)
cad.set_color(cup, "#1565C0", finish="glossy")
```

### 11.3 Small assembly: a component placed twice and colored

```python
from flywheelcad import *
cad = FlywheelCAD()

with cad.component("peg"):
    cad.with_sketch("xy")
    ctr = cad.point2d(0, 0)
    circ = cad.circle2d(ctr, 4)
    cad.radius(circle=circ, radius=4)
    body = cad.extrude("xy", cad.region(loop=[circ], inside=(0, 0)), 12)
    cad.set_color(body, "#FBC02D", finish="glossy")   # every peg is gold
    cad.component_export(body)
    cad.component_export_point("top", cad.point(0, 0, 12))

left  = cad.instance("peg", translate=(-15, 0, 0))
right = cad.instance("peg", translate=( 15, 0, 0))

# A bar bridging the two pegs' tops, snapped onto the left peg:
with cad.component("bar"):
    cad.with_sketch("xy")
    p1 = cad.point2d(0, -3); p2 = cad.point2d(30, -3)
    p3 = cad.point2d(30, 3); p4 = cad.point2d(0, 3)
    e1 = cad.line2d(p1, p2); e2 = cad.line2d(p2, p3)
    e3 = cad.line2d(p3, p4); e4 = cad.line2d(p4, p1)
    bb = cad.extrude("xy", cad.region(loop=[e1, e2, e3, e4], inside=(15, 0)), 4)
    cad.set_color(bb, "red")
    cad.component_export(bb)
    cad.component_export_point("mount", cad.point(0, 0, 0))

bar = cad.instance("bar")
cad.mate_coincident(bar, "mount", left.top)   # drop the bar onto the left peg's top
```

---

## 12. Where to look next

- `TestProjects/EXAMPLES.md` — annotated index of every example script by feature.
- `TestProjects/*.py` — focused, runnable demos (gears, lofts, booleans, drafts…).
- `Samples/AirplaneNested.fwcad/` — a real multi-file nested assembly with mates + colors.
- `FlyWheelCADV3/Resources/flywheelcad.py` — the authoritative API (read the
  docstrings for exact signatures/behavior).


---

## 13. Errors, refusals and older spellings

**The single most useful thing to know: nothing is silently accepted.** Every
renamed or removed spelling raises immediately, and the error message names the
replacement. You do not need to memorise the migration history — if you write an
older spelling, the run stops and tells you the current one. Two consequences
worth acting on: do not defensively `try/except` around `cad.*` calls (you would
be hiding the message that tells you the fix), and if a call raises, read the
message rather than guessing an alternative spelling.

### The API was frozen for publication in August 2026

A one-time renaming pass ran before the scripting API was published, on the
principle that such changes are free before publication and permanent after. If
you were trained on FlywheelCAD scripts written before that, expect these
differences — each old form now raises an `AttributeError` or `TypeError` naming
its replacement:

- **Constraint names are `snake_case`.** The older run-on lowercase spellings
  (the same words with the underscores removed) are gone. Write
  `cad.point_on_circle(...)`, `cad.equal_lines(...)`, `cad.symmetry_line(...)`,
  `cad.circle_tangent_line(...)` and so on.
- **`cad.revolve` takes `axis_line=`**, not a bare `axis=`.
- **`cad.move` is keyword-only**: `cad.move(body, translate=(10, 0, 0))`. The
  positional form and the scalar `dx=`/`dy=`/`dz=` kwargs both raise. This is the
  migration you are most likely to meet in the wild, because the app itself wrote
  the old form into every document it saved before the rename.
- **The component-export family is spelled `cad.component_export` and
  `cad.component_export_point`.** The bare `export` spellings named the same
  thing and collided with the unrelated mesh-export flag (`export=` and
  `cad.set_export`, both of which are unchanged and still current).
- **Sweep keyframes use the free function `sweep_section(fraction, plane,
  region)`.** The older bare `section(...)` free function is gone — note that
  `cad.section(body, plane)`, the analysis cross-section, is a different call and
  is unchanged.
- **Mirroring sketch elements is `cad.mirror_elements(...)`**, and an instance is
  mirrored with `cad.instance(..., mirror_plane="zx")`.
- **`cw()` / `ccw()` and `BodyRef.delete()` were removed** before publication;
  use `rev(...)` for traversal direction and `cad.delete_body(body)` to delete.
- **Colour hex strings require the `#`**, and only the four finishes `"matte"`,
  `"glossy"`, `"metallic"`, `"glass"` are accepted — the ten older finish aliases
  were removed.

### What counts as a number (September 2026)

Every argument that must be a number now applies one rule, everywhere. Before
this the rule varied by helper, so the same value could be accepted in a pattern
argument and refused in the transform argument one keyword away.

**Accepted:** `int`, `float`, and any object that is a `numbers.Number` and
answers `__float__` — which is to say `decimal.Decimal`, `fractions.Fraction`
and every numpy scalar type. A script that reads dimensions out of a CSV or a
JSON config and hands them straight to `cad.*` works.

**Refused, at the line you wrote:** strings, bytes, booleans and complex
numbers. A string of digits is not a number here: `float("30")` succeeds in
python, which is exactly why this had to be stated rather than left to the
coercion. Convert it yourself (`float(row["width"])`) — the explicit call is the
point. `numpy`'s boolean is refused with the ordinary `bool`, because
`float(True)` is `1.0` and a boolean that silently becomes 1 is a bug that shows
up as geometry, not as an error.

Two consequences worth knowing:

- **Non-`float` numeric types are converted to a double at the boundary**, so a
  `Decimal` loses the exact-decimal arithmetic it exists to provide. That is
  inherent — the document format carries doubles. A whole `Decimal` becomes a
  float, not an integer (it has no `__index__`); an integral numpy scalar does
  keep its integer form.
- **A value too large or not finite is refused by name**, whichever type it
  arrived as, rather than reaching the document as an infinity.

This tightened one previously-working spelling: a numeric **string** used to be
accepted in the pattern helpers' `spacing`/`angle`/`direction`/`center`
arguments, in the `polar`/`ring`/`grid` placement helpers, in a boolean's blend
radius, and in `cad.variable(...)`. Those now raise, with the same message the
rest of the API already gave. Pass the number.

### What raises, by category

**At author time, from python**, before anything reaches the app:

| Situation | Raises |
|---|---|
| A Ref-producing call with no assignment and no `name=` (the two tangent-line constraints) | `ValueError` naming the call |
| A `name=` that collides with an existing symbol | `ValueError` |
| `cad.variable(fixed=True, driving=True)` | `ValueError` — mutually exclusive |
| A non-`bool` passed to `export=` on any producer, or to `cad.set_export(...)` | `ValueError` |
| `cad.hide()` / `cad.show()` with no arguments | `ValueError` |
| A blend without exactly two bodies, without a radius, or with a non-positive radius; a radius without a blend | `ValueError` |
| `cad.sweep` with both `sections=` and `plane=`/`region=`, or neither; fewer than two sections; fractions not strictly increasing from exactly `0.0` to exactly `1.0`; holes in a `sections=` sweep | `ValueError` |
| `cad.path3d(closed=True)` | `ValueError` — not yet supported |
| `region()` without a `loop` | `ValueError` |
| `ref()` given a non-identifier string | `ValueError` |
| An unknown kwarg on `cad.instance(...)`, or a positional `cad.move(...)` | `TypeError` |
| A string, bytes, boolean or complex value where a number belongs — anywhere | `ValueError` naming the call and the argument |
| A number too large for a double, or not finite, in any numeric argument | `ValueError` naming the call and the argument |

**At run time, from the app**, once the command stream executes:

| Situation | Refused with |
|---|---|
| An unrecognised `quality=` or `cad.set_quality(...)` value | an error naming the five legal tiers |
| An unrecognised `cad.set_units(...)` value | an error naming the three legal units (`mm`/`cm`/`in`) |
| `cad.set_default_cell_size(...)` below `1e-6` mm, zero or negative | an error naming the `1e-6` mm floor — the same message the app's own sheet shows |
| `cad.set_default_cell_size(...)` non-finite | an error stating the value must be a finite number (same message in the sheet; note python's own `json.dumps` already rejects a literal `inf` before it gets this far) |
| An unrecognised `cad.text(align=)` value | an error naming the legal set |
| `cad.set_cell_size` below `1e-6` mm, or zero/negative | an error naming the minimum |
| A colour hex without `#`, or an unknown finish | an error naming the legal forms |
| `cad.set_quality` after the first body-creating command, more than once, or inside a component block | a named validation error; **the whole run is refused with no partial mutation** |
| `cad.set_units` more than once, or inside a component block (no after-body rule — see `FlyWheelCADSpec.md` §7.15) | a named validation error; **the whole run is refused with no partial mutation** |
| `cad.set_default_cell_size` after the first body-creating command, more than once, or inside a component block | a named validation error; **the whole run is refused with no partial mutation** |
| A mate shape the assembly rules forbid (§8.4) | a named error before the solve |

### The one door that stays silent

`BodyRef.__getattr__` turns **any** attribute access into a topology reference.
`body.v9999`, `body.vO` (letter O), `body.tpo_v0` — all of them return a ref
happily, and the failure surfaces much later and somewhere else, as an
unresolvable name during execution. This is the only place in the API where a
typo does not fail at the point of the typo.

Guard against it the way §3 rule 13 says: build reference geometry with
`cad.point(x, y, z)` and `cad.create_sketch_plane(...)` when you are not certain
which vertices a body actually exposes. The vertex naming is documented in §6.8,
but the exact set genuinely depends on how the body was made.

### When the app refuses to change a setting

Some refusals are not about your script being wrong — they are the app declining
to *edit* a script it cannot edit safely. These surface to the user as an alert
when they click a control, and the cause is almost always the shape of the
generated code rather than its correctness. The mesh-quality cases are in §C; the
Body Inspector's Apply refuses on the same principle when it cannot uniquely
target the line it would have to rewrite (an ambiguous assignment, a value bound
to a `cad.variable`, or a line whose text no longer matches). Writing plain,
module-level, single-line, literal-valued calls is what keeps every one of those
controls working.

The Edit Dimension sheet refuses on the same principle, with one deliberate
difference: a dimension bound to a `cad.variable` IS editable there (the sheet
displays that variable by name, so the user can see what they are replacing),
while a dimension bound to a python-side variable or an expression is declined
and left exactly as written. Indented and repeated-elsewhere dimension lines are
refused too. §D.6 has the full account, including the message texts.

