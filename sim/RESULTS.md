# ANN_Kicad — SPICE verification results

Simulated 2026-07-16 with ngspice 45.2. Every number below traces to a deck in
`sim/tb/` and a log in `sim/results/`. Read-only: **the schematic was not modified.**

## Verdict

| Block | Verdict |
|---|---|
| V_REF pseudo-ground (U11A) | **PASS** |
| LDR dividers (R1–R3 / R4–R6) | **PASS with a design concern** — mis-centred for room light |
| Buffers (U11 B/C/D) | **PASS** |
| Inverting stages (U1 A/B/C) | **PASS** |
| Digipot weights (U3–U8) | **PASS** — but the weight code polarity is inverted |
| Summing amps (U2 A/B/C) | **PASS** |
| **Comparator (U10 LM339)** | **FAIL — the board does not work as drawn** |
| Decoupling / PDN | **PASS** |

The analog signal chain is genuinely good: measured end-to-end against closed-form
algebra it lands within a few millivolts everywhere. **The decision stage is what
breaks the board.**

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

## CRITICAL — the LM339 cannot work in this circuit (`tb06`, `tb08`)

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

### Verified fix (`tb09`) — no part change

Attenuating **both** comparator inputs by 3 about ground preserves the comparison exactly
while moving the common-mode operating point into the valid window (N1_SUM/3 = 0.066–1.03 V,
V_REF/3 = 0.55 V). With the same real LM339 model:

| N1_SUM | Output | |
|---|---|---|
| 0.20 / 1.00 / 1.40 / 1.60 V | 0.108 V (valid LOW, LED on) | ✓ |
| 1.70 / 2.00 / 2.50 / 3.09 V | 3.294 V (valid HIGH, LED off) | ✓ |

Trip point **1.65097 V** (target 1.65). LED current **1.42 mA** on, ~0 off.
Per neuron: R_A 20k, R_B 10k on N1_SUM; R_C 20k, R_D 10k on V_REF; R_PU 10k pull-up.

**Cleaner alternative (recommended, not simulated):** replace the LM339 with a
rail-to-rail-input comparator in the same SOIC-14 quad pinout (e.g. LMV339). No attenuator,
and no loss of comparator offset margin. **Flagged as datasheet-grounds only** — no vendor
model was obtainable, so unlike the attenuator this has not been simulated.

## HIGH — no hysteresis, and no real pull-up (`tb06c`, `tb09b`)

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

| Ref | Value field | Actual part | Real value |
|---|---|---|---|
| C3 | `10nF` | CC0603KRX7R8BB104 | **100 nF** |
| C4 | `1uF` | CC0603KRX7R8BB104 | **100 nF** |
| R33 | `10k` | CRCW0603100KFKEA | **100 k** |

(C1 and C2 were checked and are consistent.) Note C3/C4 are the STM32's decoupling: if the
*parts* are right and only the labels wrong, the STM32 has 2×100nF and no 1 µF bulk —
tolerable but not what the schematic claims.

Also: **U1 and U2 unit D are parked open-loop** (`+` → +3.3 V, `−` → GND, output floating).
They will sit at the positive rail. Harmless, but tying them as followers is better practice.

## Reproducing

```
cd sim && ngspice -b tb/tb00_model_validation.cir      # validate models FIRST
                    tb/tb01_vref.cir                   # 1.64936 V
                    tb/tb02_ldr_divider.cir            # sensitivity map
                    tb/tb03_inverting.cir              # gain -0.999995
                    tb/tb04_weight_cell.cir            # +/-9.89 mV loading INL
                    tb/tb05_summer.cir                 # 0.198..3.0997 V swing
                    tb/tb06_comparator.cir             # THE FAILURE
                    tb/tb07_pdn.cir                    # 0.289 Ohm @ 204 kHz
                    tb/tb08_full_chain.cir             # end-to-end
                    tb/tb09_fixes.cir                  # verified CM fix
python3 results/count_edges.py results/tb06c_chatter.txt 1     # ~750
python3 results/count_edges.py results/tb09b_fixed_chatter.txt 1
```

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
- The LMV339 swap is recommended on datasheet grounds and has **not** been simulated.
- LED Vf was modelled (Vf ≈ 1.9 V at 1 mA); it shifts LED current, not comparator logic.
- PDN parasitics (ESR/ESL) are typical package values — the schematic carries no such data.
- Interconnect loading (each buffer/inverter drives three pot terminals, ~3.33k) is modelled
  as a lumped return to V_REF, which is the correct average case.
