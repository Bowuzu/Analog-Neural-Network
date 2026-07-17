# ANN_Kicad — SPICE verification results

Simulated 2026-07-16 with ngspice 45.2. Every number below traces to a deck in
`sim/tb/` and a log in `sim/results/`.

> **REVISION 2, 2026-07-16 — comparator changed.** The original run (revision 1)
> found the LM339 decision stage unworkable at 3.3 V. The schematic's comparator
> was subsequently changed from **LM339N (U10) → PTLV7034PWR (U9, TI TLV7034)**,
> and TB06/TB08 were rewritten and re-run against that part, plus a new TB10
> validating its model. **The failure is resolved.** Revision 1's decks and
> numbers are preserved in git at commit `f0c9fff`; the LM339 findings are kept
> below as history, clearly marked, because they are why the part changed.
>
> Revision 1 was read-only. **Revision 2 modified the schematic**: R4–R6
> 100k → **3.3k** (`CRCW06033K30FKEA`) and R34–R36 1k → **330 Ω**
> (`CRCW0603330RFKEA`), applied 2026-07-16 after TB08 pass 2 verified them.
> Both changes were simulated *before* being applied. Connectivity was proved
> unchanged by a `kicad-cli` netlist export diff (the `(nets …)` section is
> byte-identical across the edit); ERC reports 0 violations.
>
> The value change required new symbols, not just new Value fields — in this
> project the symbol name *is* the MPN (`CRCW0603100KFKEA` = 100 kΩ), so a
> Value field reading "3.3k" on a `CRCW0603100KFKEA` symbol would have ordered
> 100 kΩ. See "Schematic metadata errors" below, which is the same defect.

## Verdict

| Block | Verdict |
|---|---|
| V_REF pseudo-ground (U11A) | **PASS** |
| LDR dividers (R1–R3 / R4–R6) | **PASS** — R4–R6 changed 100k → 3.3k, recentred on ~141 lux |
| Buffers (U11 B/C/D) | **PASS** |
| Inverting stages (U1 A/B/C) | **PASS** |
| Digipot weights (U3–U8) | **PASS** — but the weight code polarity is inverted |
| Summing amps (U2 A/B/C) | **PASS** |
| **Comparator (U9 TLV7034)** | **PASS** — was FAIL on the LM339; fixed by the part change |
| LED drive (R34–R36) | **PASS** — R34–R36 changed 1k → 330 Ω, ~3 mA |
| Decoupling / PDN | **PASS** |

The analog signal chain is genuinely good: measured end-to-end against closed-form
algebra it lands within a few millivolts everywhere. The decision stage, which
broke the board in revision 1, now works.

## Models used (validated before use — `tb00_model_validation.cir`)

Both are real vendor macromodels, not approximations. TB00 exists because a model
that silently ignores a limit would produce a false pass.

| Spec | Datasheet | Model | |
|---|---|---|---|
| MCP6004 Aol | 112 dB typ | 112.7 dB | ✓ |
| MCP6004 GBW | 1 MHz typ | 1.24 MHz | ✓ |
| MCP6004 slew | 0.6 V/µs typ | 0.55 V/µs | ✓ |
| MCP6004 Vos | ±4.5 mV max | 0.64 mV | ✓ |
| MCP6004 input | rail-to-rail | tracks 0.0002 V → 3.199 V | ✓ |
| LM339 CM ceiling | Vcc−1.5 = 1.80 V | model enforces 1.30045 V | ✓ reproduces |
| TLV7034 CM range | V−…V++0.1 = 0…3.40 V | valid across 0…3.3, flag never trips | ✓ |
| TLV7034 trip point | 1.65 V | 1.6525 V | ✓ |
| TLV7034 hysteresis | 10 mV typ (3 min/25 max) | 7.03 mV (hard-coded) | ⚠ conservative |
| TLV7034 tPD | 3 µs typ | 2.988 µs | ✓ |
| TLV7034 VOL @ 3 mA | 250 mV typ / 350 max | **77 mV** | ✗ **optimistic — see below** |

- **MCP6001/2/4** — Microchip's macromodel (used for the MCP6004 quad; one datasheet
  covers the family). Obtained via a GitHub mirror after Microchip's own download 403'd.
  It carries a third-party ("Bordodynov") LTspice edit to the output stage. One line
  used LTspice's `rpar=1k` B-source extension, rewritten as an explicit parallel
  resistor — an exact equivalent, documented in-file. TB00 is what justifies trusting it.
- **LM2901/LM339** — TI's PSpice model (SLCJ010C). TI's zip `sloj046` found by search is
  mislabelled and contains an LT101x op-amp, not the LM339; the correct one is `slcj010`.
- **MCP4261** — hand-built. No vendor model exists, but the part is a resistor string
  plus a wiper tap, so a behavioural model is exact. Verified against datasheet DS22059B
  Equation 5-1: `R_WB = R_AB·N/256 + R_W`, R_W = 75 Ω typ.
- **PDV-P8103 LDR** — swept as a resistance. Datasheet (Luna, REV 10-24-16): 16–33 kΩ
  @ 10 lux, ≥0.5 MΩ dark, sensitivity γ = 0.75, **rise 60 ms / fall 25 ms**.
- **TLV7034** — TI PSpice model, literature `SLVMDH3`, from the TLV7034 product
  folder. The zip contains a netlist named `tlv7031.lib`: expected, since the quad
  is four copies of the TLV703x die. Its header says "Part: TLV7011 / Datasheet:
  SLVSDM5F" though the subcircuit is `TLV7031` — TI appears to have derived the
  TLV703x model from the TLV701x one, which matters for exactly one number
  (hysteresis, see TB10). Unmodified apart from CRLF→LF. A wrapper subcircuit
  adapts TI's port order `(IN+ IN- OUT V+ V-)` to this project's house order
  `(IN+ IN- Vcc GND OUT)` rather than silently re-ordering ports at each call
  site — a mistake that would still simulate. Provenance is documented in full
  in `models/TLV7034.lib`. **TB10 is what justifies trusting it.**

## RESOLVED — the comparator now works (`tb06`, `tb08`, `tb10`)

The LM339 finding below was correct and is unchanged. The part was swapped for a
**TLV7034** (quad, TSSOP-14, push-pull, rail-to-rail input, internal hysteresis),
which addresses it structurally rather than by adding a network around a part that
was the wrong choice at 3.3 V.

The netlist was re-extracted from `ANN_Kicad.kicad_sch` and checked pin by pin —
this was not assumed. The LM339 and TLV7034 pinouts are **completely different**
(V<sub>CC</sub> moves 3→4, GND 12→11, and every input/output moves), and all 14
pins landed correctly: `+IN A/B/C` = N1/N2/N3_SUM, `−IN A/B/C` = V_REF_BUF, pin 4
= +3.3 V with C15, pin 11 = GND, channel D parked with a no-connect on OUT D.

**TB06(A) — as designed, IN− = V_REF_BUF = 1.65 V.** The exact test that produced
a stuck output on the LM339:

| N1_SUM | Output | |
|---|---|---|
| 0.20 / 1.00 / 1.40 / 1.60 V | 0.0568 V (valid LOW, LED on) | ✓ |
| 1.70 / 2.00 / 3.10 V | 3.282 V (valid HIGH, LED off) | ✓ |

Trip point **1.65247 V** (target 1.65; the +2.5 mV is half the model's hysteresis
window). Output range across the whole 0–3.3 V sweep: **0.0568 … 3.282 V** —
both rails reached, nothing stuck at mid-supply.

**TB06(B) — common-mode map.** On the LM339 this sweep located a ceiling at
1.30045 V. On the TLV7034 the output holds a valid HIGH at 1.30, 1.40, 1.80, 2.50
and 3.10 V. **There is no ceiling anywhere in the operating range.**

**TB08 — full chain.** OUT range across the LDR sweep is **0.0568 … 3.282 V**,
against revision 1's **1.65005 … 1.65005** (stuck). The decision stage is live.

### Why this is a structural fix, not a patch

The TLV7034's V<sub>CM</sub> is V<sub>EE</sub> to V<sub>CC</sub>+0.1 = **0 to 3.40 V** at
3.3 V, so the entire 0.198–3.0997 V swing *and* the 1.65 V reference sit inside it
with margin. The LM339 wanted a 5 V rail; nothing about 3.3 V operation was
recoverable by biasing.

**Three planned remedies are now unnecessary and should NOT be built:**

| Revision 1 remedy | Parts | Status |
|---|---|---|
| ÷3 attenuator on both inputs (TB09) | 12 resistors | **not needed** — RRI. Would also throw away 3× of signal against a ±8 mV V<sub>os</sub> |
| 10k pull-ups on the outputs | 3 resistors | **not needed** — push-pull |
| 4.7 MΩ hysteresis feedback | 3 resistors | **not needed** — 10 mV internal |

`tb09_fixes.cir` is retained for the record but is **obsolete**; it verifies the
attenuator fix for a part no longer on the schematic.

### Honest limits of this result

- **The model's V<sub>OL</sub> is optimistic and cannot size the LED.** TB10(C)
  measured 77 mV at 3 mA against a datasheet 250 mV typ / 350 mV max. The output
  stage is two idealised BJTs (`NPN1`/`PNP1`, LEVEL=1, `RC=1`) — modelled, not
  characterised. Every LED current from TB06/TB08 is an **upper bound**. R34–R36
  are sized from the datasheet below, not from simulation.
- The model's hysteresis is hard-coded at 7 mV vs a 10 mV datasheet typ. That is
  conservative (chatter results are pessimistic), and still above the 3 mV min.
- The model flags out-of-range only above an **absolute 6 V**, not V<sub>CC</sub>+0.1.
  It is therefore optimistic *above the rail only*; N1_SUM peaks at 3.10 V, so this
  never affects a conclusion here. TB10(B) measures it directly.
- V<sub>os</sub> is ±8 mV max (worse than the LM339's ±5 mV). With the hysteresis
  window that puts roughly **±20 mV** of uncertainty on the 1.65 V trip point. It is
  systematic, so the bias digipot absorbs it — but it is not zero.

## HISTORY (revision 1) — the LM339 cannot work in this circuit (`tb06`, `tb08`)

**Superseded by the part change above.** Retained because it is the evidence base
for that change. The numbers below were produced with the LM339 decks at `f0c9fff`.

This is not a marginal call. It has two independent proofs.

**1. Datasheet arithmetic (no simulation needed).** The LM339's input common-mode range
at Vcc = 3.3 V is 0 to Vcc−1.5 = **1.80 V**. TB05 measured N1_SUM's actual swing as
**0.198 V … 3.0997 V** (matching the closed-form 0.198/3.102 exactly). So roughly 42% of
N1_SUM's range sits above the guaranteed common-mode ceiling. Worse, `V_REF_BUF` — the
comparator's *other* input, permanently at 1.65 V — has only **150 mV** of margin to that
ceiling, and TB01 measured **±16.5 mV** of spread from the 1% R7/R8 tolerance alone,
before temperature.

**2. TI's own model refuses to predict.** Its `INPUTRANGE` block enforces Vcc−2.0; TB06(B)
located the ceiling at **1.30045 V**. Because the 1.65 V reference is *itself* above that,
TB06(A) swept N1_SUM across the full 0–3.3 V and the output never changed: **stuck at
1.65005 V at every single point**. TB08 reproduced this on the complete chain.

> The 1.65 V output is **not** a physical prediction. It is TI's Output_Stage being forced
> to mid-supply by its `SMID` switch — a "this model is outside its validity region" flag.
> Real silicon does something else (typically phase inversion or a stuck output). That
> ambiguity *is* the point: the datasheet does not guarantee behaviour here, so the part's
> response is undefined. **Do not read "the LEDs glow dimly at 52 µA" as a prediction** —
> it is an artefact of the flag.

The root cause is structural: the LM339 wants a mid-rail reference at **5 V** (where the
ceiling is 3.5 V and 2.5 V sits comfortably inside). At 3.3 V it is simply the wrong part.

### Verified fix (`tb09`) — no part change — **OBSOLETE, do not build**

Attenuating **both** comparator inputs by 3 about ground preserves the comparison exactly
while moving the common-mode operating point into the valid window (N1_SUM/3 = 0.066–1.03 V,
V_REF/3 = 0.55 V). With the same real LM339 model:

| N1_SUM | Output | |
|---|---|---|
| 0.20 / 1.00 / 1.40 / 1.60 V | 0.108 V (valid LOW, LED on) | ✓ |
| 1.70 / 2.00 / 2.50 / 3.09 V | 3.294 V (valid HIGH, LED off) | ✓ |

Trip point **1.65097 V** (target 1.65). LED current **1.42 mA** on, ~0 off.
Per neuron: R_A 20k, R_B 10k on N1_SUM; R_C 20k, R_D 10k on V_REF; R_PU 10k pull-up.

**Superseded.** The part change removes the need for this network entirely.

**Cleaner alternative (recommended, not simulated):** replace the LM339 with a
rail-to-rail-input comparator in the same SOIC-14 quad pinout (e.g. LMV339). No attenuator,
and no loss of comparator offset margin. **Flagged as datasheet-grounds only** — no vendor
model was obtainable, so unlike the attenuator this has not been simulated.

> **Outcome:** this recommendation was taken, with a better part than the one
> suggested — the TLV7034 (TSSOP-14, not the same pinout as the LM339) adds
> internal hysteresis and a push-pull output, which the LMV339 would not have
> provided. It *is* now simulated: TI ships a model for it, and TB10 validates it.

## HISTORY (revision 1) — no hysteresis, and no real pull-up (`tb06c`, `tb09b`)

**Resolved by the part change.** The TLV7034's internal hysteresis (10 mV typ,
3 mV min, 25 mV max) and push-pull output address both halves of this finding.

**TB06(C) re-run on the TLV7034, at the real 1.65 V reference:** identical stimulus
(0.5 V/s ramp, 2 mV 100 Hz flicker at worst-case phase 180, 200 µV RMS broadband
noise) now produces **exactly 1 transition, chatter window 0.000 ms** — reproduced
on three consecutive runs with independent noise seeds, where revision 1's count
varied stochastically around 750.

Note revision 1 had to relocate the reference to 1.0 V to test hysteresis at all,
because 1.65 V was outside the LM339's valid range and the two questions could not
otherwise be separated. **The re-run tests the real 1.65 V reference** — that is
the point of the part change.

One honest caveat: the model's 7 mV hysteresis clears the modelled 4 mV pk-pk
flicker comfortably, but a worst-case **3 mV min** part would be marginal against
it. This does not matter while only LEDs are driven; if firmware ever reads these
pins, the datasheet (§7.1.1) shows external positive feedback to widen the window.

The original finding follows.

### Original finding

A single slow threshold crossing with realistic mains flicker produced **~750 output
transitions** where there should be 1 (747 and 753 on two runs — the noise is randomly
seeded per run, so counts vary slightly; the magnitude is reproducible). The chatter spans a
**7.5 ms window**. The condition is phase-independent: chatter occurs
whenever interference slew exceeds signal slew — here 2 mV of 100 Hz flicker slews at
1.26 V/s against the signal's 0.5 V/s, so **any flicker above ~0.8 mV chatters this
comparator.** The LDR's 60 ms rise time guarantees slow crossings, so this is the normal case.

Compounding it: there is **no pull-up on 1OUT**. The only path to +3.3 V is R30 (1k) in
series with the LED, and an LED at sub-mA current is a very high dynamic impedance. A
pull-up is a *prerequisite* for hysteresis, not a nicety.

**Honest status of the hysteresis fix: partial.** Adding a 10k pull-up plus a 4.7 MΩ
feedback resistor cut the chatter *window* from 7.5 ms to 0.018 ms, but did not eliminate
edges (~750 → 37–89; the exact count is stochastic across noise realisations, so treat the
window, not the count, as the real measure). The residual is a genuine design tension I
could not resolve with a discrete network on this part: small hysteresis demands a large
R_H, but R_H · C_in (4.7 MΩ × ~1 pF = 4.7 µs) then exceeds the LM339's ~1.3 µs propagation
delay, so the hysteresis arrives after the output has already flipped. Attempts at
R_H = 1 MΩ produced a *false pass* (0 transitions — because 63 mV of hysteresis simply
exceeded the test ramp, so it never switched at all), and a lower-impedance redesign
failed to converge. **A comparator with built-in hysteresis is the robust answer.**

Mitigating context: nothing reads these outputs — they drive LEDs only, and the STM32 does
not sense them. Microsecond chatter is invisible on an LED. Fix the common-mode problem
first; hysteresis matters only if firmware ever reads these pins, or for EMI.

## MEDIUM — the LDR dividers are mis-centred for room light (`tb02`)

The 100k fixed resistor puts peak sensitivity where R_LDR = 100k, which per γ = 0.75
corresponds to **≈1.5 lux** — near darkness.

| Light | R_LDR | V_BUF_IN | Sensitivity |
|---|---|---|---|
| ~900 lux | 1 k | 3.267 V | — |
| ~100 lux (room) | 4.3 k | 3.164 V | **0.300 V/decade** |
| 10 lux | 23 k | 2.683 V | 1.155 V/decade |
| ~1.5 lux | 100 k | 1.650 V | **1.900 V/decade** ← peak |
| dark | 500 k | 0.550 V | 1.055 V/decade |

Measured peak **1.89968 V/decade** against theory `Vdd·ln(10)/4 = 1.899` — an exact match,
which is a good independent check that the sweep is right.

In ordinary room light all three inputs sit near 3.16 V (v ≈ +1.5, close to the maximum),
so the network runs with its inputs nearly saturated and little dynamic range. It works
well only in dim light. **If room-light operation is wanted, drop R4–R6 to ~4.7k–10k**;
that recentres peak sensitivity onto 50–200 lux. (You chose "sweep wide", so this is
offered as information, not a defect.)

### Sizing rule and the proposed value (`tb08` pass 2)

The rule is exactly **R_fixed = R_LDR at the light level you want to sit at** — that
is where v = 0 and sensitivity peaks. R_fixed slides the curve; it cannot change its
shape.

| R_fixed | Centres v = 0 at |
|---|---|
| 100k (as drawn) | 1.5 lux (near dark) |
| 10k | 32 lux |
| 4.7k | 88 lux |
| **3.3k (proposed)** | **141 lux — typical room** |
| 2.2k | 242 lux — desk lamp |

TB08 pass 2 simulates R4–R6 = 3.3k end-to-end through the real chain:

| R_LDR1 | ≈ lux | V_BUF_1 | N1_SUM | OUT |
|---|---|---|---|---|
| 760 Ω | ~1000 | 2.682 V | 1.421 V | LOW (LED on) |
| 3.3k | ~141 | **1.649 V** | **1.648 V** | LOW (at the trip) |
| 24k | ~10 | 0.398 V | 1.923 V | HIGH (LED off) |
| 500k | dark | 0.021 V | 2.006 V | HIGH (LED off) |

The divider centre lands **exactly on the trip point** (V_BUF_1 = 1.649 V against a
predicted 1.650). Measured LED switch-over at **R_LDR1 = 3348.8 Ω** against the
predicted 3300 — the 1.5% is V_REF's −0.64 mV op-amp V<sub>os</sub> plus the
comparator's 3.5 mV half-hysteresis, i.e. ~2% in lux terms. Negligible.

**Side benefit — this also fixes the ADC finding below for free.** Thevenin source
impedance at the STM32's ADC pins is R_fixed ∥ R_LDR, so it drops from **98 kΩ
worst-case to ≤3.3 kΩ** at every light level.

### The limit R_fixed cannot fix

Sensitivity at the centre is **1.425 V per decade of illuminance**
(= V<sub>dd</sub>·γ·ln10/4). This is set by γ and the divider topology and is
**independent of R_fixed**. Consequences worth designing around:

- Spanning the full ±1.65 V input range needs ~2.3 decades of light — a **200:1
  scene contrast**. A realistic 10:1 contrast uses only ±0.43 of the normalized
  ±1 range. More swing requires gain after the divider, which this board does not
  have (U11 buffers are ×1, U1 inverters are ×1).
- The PDV-P8103's 16–33 kΩ spread at 10 lux means the three cells centre anywhere
  from **82 to 215 lux** with R_fixed = 3.3k. That is a per-channel offset — exactly
  what the bias digipots exist to trim — so it is absorbed, not a defect.
- Dark resistance is **not a design constraint**: it only needs to be ≫ R_fixed so
  the divider bottoms out. ≥0.5 MΩ against 3.3k is 150×, already far more than
  needed. The *bright* end is the real limit — at ~1000 lux the LDR is only ~760 Ω,
  so V_BUF tops out at 2.68 V and never reaches the rail.

## MEDIUM — LED drive current is dim (`tb06`, datasheet)

R34–R36 = 1k gives **~1.2 mA**. The Würth 151051RS11000 is 30 mcd at 20 mA, so at
1.2 mA it produces roughly **1.9 mcd** — visible only in a dim room.

**This number is from the datasheet, not the simulation.** TB10(C) established that
the model's V<sub>OL</sub> is optimistic (77 mV vs 250 mV typ at 3 mA), so TB06's
1.47 mA and TB08's 4.18 mA are upper bounds. Solving
`I = (3.3 − Vf(I) − V_OL(I))/R` with the datasheet's V<sub>OL</sub> slope
(250 mV/3 mA ≈ 83 Ω typ, 350 mV/3 mA ≈ 117 Ω max):

| R34–R36 | I_LED (datasheet-based) | Brightness | |
|---|---|---|---|
| 1k (as drawn) | 1.2 mA | ~1.9 mcd | dim |
| 470 Ω | 2.3 mA | ~3.5 mcd | |
| **330 Ω (proposed)** | **~3.0–3.2 mA typ, 2.9 mA at max V_OL** | ~4.6 mcd | at the specified V<sub>OL</sub> point |
| 220 Ω | ~4 mA | ~6.0 mcd | fine (I<sub>SC</sub> = 33 mA) but V<sub>OL</sub> unspecified there |

**330 Ω is the recommendation**: 3 mA is the current at which the TLV7034's
V<sub>OL</sub> is actually guaranteed, so it is the brightest point that stays
inside the datasheet. 1k is not *wrong* — just dim.

Keep the LED on the +3.3 V side sinking into the output, as drawn: sink drive
(33 mA I<sub>SC</sub>) is stronger than source (29 mA), and V<sub>OL</sub> is the
specified parameter.

## MEDIUM — weight and bias code polarity are inverted (`tb04`, `tb05`)

Confirmed against MCP4261 datasheet DS22059B: the wiper-code table states **"Zero Scale
(W = B)"** at code 000h and **"Full Scale (W = A)"** at 100h. Since terminal B is
`V_BUF_n_OUT` (=1.65+v) and terminal A is `INV_V_n` (=1.65−v):

**w = 1 − 2D/256**, i.e. D=0 → w = **+1**, D=256 → w = **−1**. Increasing the code makes the
weight *more negative*. The bias pots are likewise inverted: code 0 → wiper = +3.3 V.

This is **not a hardware fault** — w=0 still lands at D=128 and the range is still [−1,+1] —
but it is the opposite of the natural expectation and the STM32 firmware must get it right.

Worth noting the sign chain works out correctly overall: the digipot's inverted polarity and
the summer's inversion **cancel**, so the neuron fires (LED on) when Σ wᵢvᵢ > 0. That is
correct neuron semantics, arrived at by two inversions cancelling rather than by design intent.

## LOW / INFO

- **Digipot wiper loading** (`tb04`): max weight error **±9.89 mV** (theory predicted ±9.6),
  peaking at D≈202/54 where wiper Rth is largest. Rth peaks at **2575 Ω = R_AB/4 + R_W**,
  exactly as predicted. That is **1.27 LSB** — slightly over one code — but it is a smooth,
  monotonic, predictable INL (a mild compression of the weight curve), not noise. Weight
  training or calibration absorbs it. Not worth changing anything for.
- **ADC source impedance** (`tb02`): `V_BUF_IN_n` also feeds STM32 ADC pins PA0–PA2 with a
  Thevenin impedance of **18.7 kΩ at 10 lux, 50 kΩ worst case, 83 kΩ in the dark**, with no
  series resistor and no sampling capacitor. The STM32F030 wants a low source impedance to
  charge its sampling cap; use the longest sampling time, or add a ~10–100 nF cap at the pin.
  The buffered path (via U11) is unaffected — this only concerns the ADC readback.
  **Note:** the proposed R4–R6 = 3.3k change caps this at **≤3.3 kΩ** at every light
  level, which resolves the finding without a series resistor or a cap. If R4–R6 stay
  at 100k, this stands as written.
- **Decoupling / PDN** (`tb07`): **healthy.** |Z| ≈ 50 mΩ from DC to 10 kHz (feed-resistance
  limited), 100 mΩ at 100 kHz. Real bulk-vs-ceramic anti-resonance is only **0.289 Ω at
  204 kHz**, rising to **0.488 Ω at 263 kHz** once C2 is derated for DC bias (X5R 4.7 µF/0603
  loses ~half its value at 3.3 V). All sub-ohm. This board's transients are tiny — 1.2 mA of
  near-constant op-amp Iq, a few mA for the STM32, SPI edges into 6 CMOS inputs. No DC-DC, no
  fast bus. The 11×100nF + 4.7 µF is entirely adequate. **No change needed.**
- **Noise** (`tb05`): 18.6 µV RMS at the sum vs a 1.72 mV weight LSB — about 1% of an LSB.
  Not a limitation.
- **Bandwidth**: every stage is 4–5 decades faster than the signal (inverter f₃dB 392 kHz,
  summer 568 kHz; the LDR rolls off at 10–25 Hz). Bandwidth is a non-issue on this board.
- **V_REF accuracy** (`tb01`): 1.64936 V (−0.64 mV, all op-amp Vos). The 1% R7/R8 tolerance
  contributes **±16.5 mV**, which is a *systematic* offset shared by all three neurons.
  |Zout| 7.5 mΩ at DC.

## Schematic metadata errors (verified, not simulated)

Value fields disagree with the actual symbol/MPN — these will produce a wrong BOM:

**All resolved as of 2026-07-16.** In every case the *label* turned out to be the design
intent and the *part* was wrong, confirmed by the author. Kept as the record:

| Ref | Value field | Was (wrong part) | Now | Status |
|---|---|---|---|---|
| R4–R6 | `3.3k` | CRCW0603100KFKEA (100k) | CRCW06033K30FKEA | **fixed** |
| R34–R36 | `330` | CRCW06031K00FKEA (1k) | CRCW0603330RFKEA | **fixed** |
| R33 | `10k` | CRCW0603100KFKEA (100k) | RC0603FR-0710KL | **fixed** — needs rewiring, see below |
| C3 | `10nF` | CC0603KRX7R8BB104 (100nF) | CC0603KRX7R8BB103 | **fixed** |
| C4 | `1uF` | CC0603KRX7R8BB104 (100nF) | CC0603KRX7R8BB105 | **fixed** |

(C1 and C2 were checked and were already consistent.)

**R33 is the NRST pull-up** (IC1 pin 4 → +3.3 V), not a signal resistor — 10k is the
conventional value. **C3/C4 are VDDA decoupling** (IC1 pin 5); C1/C2 (100nF + 4.7 µF) are
on VDD (pin 16). So the STM32 now has 10nF + 1µF on VDDA as drawn, rather than the
2×100nF it actually had.

> **R33 needs its wires reconnected by hand** (3 ERC errors, deliberately left).
> R33 was pointed at the project's existing 10k (`RC0603FR-0710KL`, as used by R7–R14)
> rather than cloning a Vishay `CRCW060310K0FKEA`, so the BOM carries **one** 10k line
> item instead of two. The cost is that the symbols have incompatible geometry:
>
> | | pin spacing | origin |
> |---|---|---|
> | `CRCW0603100KFKEA` (old) | 10.16 mm | centred between pins |
> | `RC0603FR-0710KL` (new) | 12.70 mm | on pin 1 |
>
> The old part's pins landed exactly on the +3.3 V symbol (114.30, 53.34) and the NRST
> wire (114.30, 63.50) with no wires at all. The new part's land at 58.42 and 71.12.
> **The 2.54 mm spacing difference means no amount of nudging fixes it** — putting pin 1
> on +3.3 V forces pin 2 to 66.04, and the NRST wire is at 63.50. Reconnecting is a
> deliberate manual step, not an oversight.

> **Library defect found and fixed:** the `10nF_0603` download typed its pins
> `unspecified`, where its own 100nF sibling from the same vendor/tool types them
> `passive`. That produced 2 spurious ERC warnings on C3. Corrected in
> `~/Kicad Footprints/10nF_0603/KiCADv6/2026-07-13_22-15-31.kicad_sym` (4 pins) — a
> capacitor has no unspecified pins. Backup in the session scratchpad.

> **This is the project's most repeatable failure mode, so it is worth naming.**
> Every part here is an UltraLibrarian-style download in
> `~/Kicad Footprints/<MPN>/`, registered in the **global** library tables (the
> project's own `sym-lib-table`/`fp-lib-table` are empty). The symbol name *is* the
> MPN, so **editing the Value field changes the label and nothing else** — the part
> ordered is still whatever the symbol is named. R4–R6 and R34–R36 were initially
> changed this way and read "3.3k"/"330" while still *being* the 100k and 1k parts;
> that is how they came to be listed here before being fixed properly.
>
> Changing a value therefore means pointing the symbol at a different MPN library,
> not retyping a field. For R4–R6 and R34–R36 this was done by cloning the existing
> CRCW0603 symbol/footprint (the 0603 land pattern `RESC1508X50N` is identical
> across the family) to `CRCW06033K30FKEA` and `CRCW0603330RFKEA`, and registering
> both in the global tables.
>
> **R33 is the one to decide next**: is it meant to be 10k or 100k? The label and
> the part disagree, and only one of them is what you intended.

Also: **U1 and U2 unit D are parked open-loop** (`+` → +3.3 V, `−` → GND, output floating).
They will sit at the positive rail. Harmless, but tying them as followers is better practice.

## Reproducing

```
cd sim && ngspice -b tb/tb00_model_validation.cir      # validate models FIRST
                    tb/tb10_tlv7034_validation.cir     # validate TLV7034 model FIRST
                    tb/tb01_vref.cir                   # 1.64936 V
                    tb/tb02_ldr_divider.cir            # sensitivity map
                    tb/tb03_inverting.cir              # gain -0.999995
                    tb/tb04_weight_cell.cir            # +/-9.89 mV loading INL
                    tb/tb05_summer.cir                 # 0.198..3.0997 V swing
                    tb/tb06_comparator.cir             # now PASSES (was THE FAILURE)
                    tb/tb07_pdn.cir                    # 0.289 Ohm @ 204 kHz
                    tb/tb08_full_chain.cir             # end-to-end, 2 passes
                    tb/tb09_fixes.cir                  # OBSOLETE (LM339 attenuator)
python3 results/count_edges.py results/tb06c_chatter.txt 1     # 1  (was ~750)
```

TB06(C)'s noise is randomly seeded per run. The 1-transition result reproduced on
three consecutive runs; revision 1's ~750 varied run to run, so the chatter
*window* (0.000 ms now, 7.5 ms then) is the more meaningful measure.

TB08 runs two passes in one deck — "as drawn" (R4–R6 = 100k, R34 = 1k) and
"proposed" (3.3k / 330 Ω) — writing `tb08_chain_sweep_asdrawn.txt` and
`tb08_chain_sweep_proposed.txt`. The comparator change applies to both: it is a
correctness fix and is not conditional on the resistor values.

Decks must be run **from `sim/`**: ngspice resolves `.include` relative to the deck but
`wrdata` relative to the CWD. `sim/.spiceinit` sets `ngbehavior=ps` — both vendor models are
PSpice syntax and will not parse without it.

## Caveats

- The comparator failure rests on datasheet arithmetic (guaranteed CM range 1.80 V vs a
  measured 0.198–3.0997 V swing). Simulation *illustrates* it; it does not by itself prove
  what real silicon does above the limit, because nothing does — that is what "outside the
  guaranteed range" means.
- The LM339 model's 1.30 V ceiling is more conservative than the datasheet's 1.80 V. The
  conclusion holds under either number, but the exact simulated behaviour reflects the model's.
- **The TLV7034 result is now simulated, not just calculated** — but its model's
  V<sub>OL</sub>/V<sub>OH</sub> are optimistic (TB10(C)), so no LED current in this
  document comes from simulation; R34–R36 are sized from the datasheet.
- The TLV7034's V<sub>CM</sub> pass is a *guaranteed*-range result: 0 to V<sub>CC</sub>+0.1
  covers the full swing with margin, so unlike the LM339 case there is no reliance on
  undefined behaviour.
- LED Vf was modelled (Vf ≈ 1.9 V at 1 mA); it shifts LED current, not comparator logic.
- R4–R6 = 3.3k and R34–R36 = 330 Ω are **applied to the schematic** (2026-07-16),
  having been simulated first. TB08 pass 1 is retained as the record that the board
  also works with the new comparator at the *old* 100k/1k values — the comparator fix
  and the resistor changes are independent, and pass 1 is what proves that.
- The three LDR cells' centre light level varies **82–215 lux** part-to-part from the
  PDV-P8103's 16–33 kΩ spread. Bias training absorbs it, but the board is not
  calibrated out of the box.
- PDN parasitics (ESR/ESL) are typical package values — the schematic carries no such data.
- Interconnect loading (each buffer/inverter drives three pot terminals, ~3.33k) is modelled
  as a lumped return to V_REF, which is the correct average case.
