#!/usr/bin/env python3
"""Count comparator output transitions in an ngspice wrdata transient export.

ngspice's deriv() chokes on square waveforms (polyfit failure), so edges are
counted here instead. A transition is a crossing of mid-supply; a small
dead-band stops a single noisy edge from being counted many times.

Usage: count_edges.py <wrdata file> [column]
The wrdata format written by these decks is: time v(outc) time v(nflick) ...
so the output column of interest is column 1.
"""
import sys

path = sys.argv[1]
col = int(sys.argv[2]) if len(sys.argv) > 2 else 1

t, v = [], []
with open(path) as fh:
    for line in fh:
        parts = line.split()
        if len(parts) <= col:
            continue
        try:
            t.append(float(parts[0]))
            v.append(float(parts[col]))
        except ValueError:
            continue

VDD = 3.3
hi, lo = 0.7 * VDD, 0.3 * VDD  # dead-band around mid-supply

state = None
edges = []
for ti, vi in zip(t, v):
    if vi > hi and state != 1:
        if state is not None:
            edges.append((ti, "LOW->HIGH"))
        state = 1
    elif vi < lo and state != 0:
        if state is not None:
            edges.append((ti, "HIGH->LOW"))
        state = 0

print(f"file            : {path}")
print(f"samples         : {len(v)}")
print(f"output range    : {min(v):.4f} .. {max(v):.4f} V")
print(f"transitions     : {len(edges)}")
if edges:
    print(f"first transition: t = {edges[0][0]*1e3:.3f} ms ({edges[0][1]})")
    print(f"last  transition: t = {edges[-1][0]*1e3:.3f} ms ({edges[-1][1]})")
    print(f"chatter window  : {(edges[-1][0]-edges[0][0])*1e3:.3f} ms")
    print(f"expected        : 1 transition for a single threshold crossing")
    if "-v" in sys.argv:
        print()
        print("all transitions:")
        for ti, kind in edges:
            print(f"  t = {ti*1e3:9.4f} ms   {kind}")
    else:
        print("(pass -v to list every transition)")
else:
    print("NO transitions -- output never crossed the dead-band.")
    print("If the output sits near mid-supply, the LM339 macromodel is")
    print("signalling that its inputs are outside the valid common-mode range.")
