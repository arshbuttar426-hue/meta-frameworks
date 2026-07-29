#!/usr/bin/env python3
# ============================================================
# MASSIVE 26x4 CORNER-MARK DECODER
# ============================================================
# Complete A-Z grid with 26 letters, 4 corners each.
# Corner marks: 0=empty, 1=dot, 2=tick
# 
# TO ADD YOUR ONE CLUE:
# Find any letter below with value=None, replace None with the real number.
# Example: 'X': {'corners': (0, 2, 1, 0), 'value': 1.23},
# Then run: python massive_decoder.py
# ============================================================

import json
import math
import os
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------

CONFIG = {
    'lambda_complexity': 0.3,
    'noise_gamma': 0.1,
    'small_sigma_penalty': 5.0,
}

VARS = ['TL', 'TR', 'BL', 'BR']

# ------------------------------------------------------------------
# FULL A-Z DATASET
# ------------------------------------------------------------------
# 26 letters. 5 known (B,C,D,E,F). 21 unknown (including U).
# EDIT HERE: Change any 'value': None to 'value': YOUR_NUMBER

DATA = {
    'A': {'corners': (0, 0, 2, 0), 'value': 6.0},    # '8'
    'B': {'corners': (0, 0, 2, 1), 'value': 7.0},    # '9'
    'C': {'corners': (1, 2, 2, 2), 'value': 53.0},   # 'g'
    'D': {'corners': (2, 1, 2, 2), 'value': 71.0},   # 'y'
    'E': {'corners': (2, 1, 2, 2), 'value': 71.0},   # 'y'
    'F': {'corners': (0, 0, 1, 1), 'value': 4.0},    # '6'
    'G': {'corners': (0, 0, 1, 0), 'value': 3.0},    # '5'
    'H': {'corners': (2, 0, 0, 0), 'value': 54.0},   # 'h'
    'I': {'corners': (1, 2, 1, 2), 'value': None},   # Target: 'd' (50.0)
    'J': {'corners': (2, 0, 0, 1), 'value': None},   # Target: 'i' (55.0)
    'K': {'corners': (2, 0, 0, 0), 'value': None},   # Target: 'h' (54.0)
    'L': {'corners': (0, 0, 0, 0), 'value': None},
}

# ------------------------------------------------------------------
# BAYESIAN SCORING
# ------------------------------------------------------------------

def bayesian_score(mse: float, complexity: int, node_count: int, n: int, config: Dict) -> float:
    sigma = math.sqrt(max(mse, 1e-10))
    log_likelihood = -0.5 * n * math.log(2 * math.pi * sigma**2) - (mse * n) / (2 * sigma**2)
    bic = -0.5 * node_count * math.log(n)
    complexity_prior = -config['lambda_complexity'] * complexity
    gamma = config['noise_gamma']
    pen = config['small_sigma_penalty']
    noise_prior = -pen * math.log(sigma / gamma + gamma / sigma)
    return log_likelihood + bic + complexity_prior + noise_prior

# ------------------------------------------------------------------
# HYPOTHESIS CLASS
# ------------------------------------------------------------------

@dataclass
class Hypothesis:
    name: str
    category: str
    formula_str: str
    evaluator: callable
    complexity: int
    node_count: int
    mse: float = 0.0
    score: float = 0.0
    sigma: float = 0.0
    predictions: Dict[str, float] = None

    def evaluate(self, corners: Tuple[int, int, int, int]) -> float:
        return self.evaluator(*corners)

# ------------------------------------------------------------------
# GENERATE HYPOTHESIS CATALOG
# ------------------------------------------------------------------

def build_catalog() -> List[Hypothesis]:
    hypotheses = []

    # SINGLE VARIABLE
    for i, var in enumerate(VARS):
        hypotheses.append(Hypothesis(
            name=f"just_{var}", category="single_var",
            formula_str=var,
            evaluator=lambda tl, tr, bl, br, idx=i: [tl, tr, bl, br][idx],
            complexity=1, node_count=1))

    # LINEAR: (w1*TL + w2*TR + w3*BL + w4*BR + b) / denom
    for w1 in range(-3, 4):
        for w2 in range(-3, 4):
            for w3 in range(-3, 4):
                for w4 in range(-3, 4):
                    for b in range(-3, 4):
                        for denom in [1, 2, 3, 4, 5, 10]:
                            if w1 == w2 == w3 == w4 == 0:
                                continue
                            cplx = sum(1 for w in [w1,w2,w3,w4] if w != 0) + (1 if denom > 1 else 0)
                            def make_lin(a,b,c,d,e,f):
                                return lambda tl,tr,bl,br: (a*tl + b*tr + c*bl + d*br + e) / f
                            name = f"lin_{w1}{w2}{w3}{w4}_b{b}_d{denom}"
                            formula = f"({w1}*TL + {w2}*TR + {w3}*BL + {w4}*BR + {b}) / {denom}"
                            if len(formula) < 60:
                                hypotheses.append(Hypothesis(
                                    name=name, category="linear", formula_str=formula,
                                    evaluator=make_lin(w1,w2,w3,w4,b,denom),
                                    complexity=cplx + 2, node_count=cplx + 3))

    # BILINEAR
    for a in range(-5, 6):
        for b in range(-5, 6):
            for c in range(-5, 6):
                for d in range(-5, 6):
                    for denom in [1, 2, 3, 4, 5, 10, 20]:
                        if a == 0 and b == 0:
                            continue
                        if c == 0 and d == 0:
                            continue
                        def make_rat(a,b,c,d,e):
                            return lambda tl,tr,bl,br: (a + b*tl) * (c + d*bl) / e
                        hypotheses.append(Hypothesis(
                            name=f"rat_{a}_{b}_{c}_{d}_d{denom}", category="interaction",
                            formula_str=f"({a}+{b}*TL)*({c}+{d}*BL)/{denom}",
                            evaluator=make_rat(a,b,c,d,denom),
                            complexity=6, node_count=7))

    # SYMMETRIC
    hypotheses.append(Hypothesis("sum_div4", "symmetric", "(TL+TR+BL+BR)/4",
        lambda tl,tr,bl,br: (tl+tr+bl+br)/4, 3, 4))
    hypotheses.append(Hypothesis("sum_div2", "symmetric", "(TL+TR+BL+BR)/2",
        lambda tl,tr,bl,br: (tl+tr+bl+br)/2, 3, 4))
    hypotheses.append(Hypothesis("sum", "symmetric", "TL+TR+BL+BR",
        lambda tl,tr,bl,br: tl+tr+bl+br, 2, 4))
    hypotheses.append(Hypothesis("pair_prod_sum", "symmetric", "TL*TR + BL*BR",
        lambda tl,tr,bl,br: tl*tr + bl*br, 3, 4))
    hypotheses.append(Hypothesis("pair_sum_prod", "symmetric", "(TL+BL)*(TR+BR)",
        lambda tl,tr,bl,br: (tl+bl)*(tr+br), 3, 4))

    # BASE-3
    orders = [
        ('TL-TR-BL-BR', [0,1,2,3]), ('BL-BR-TL-TR', [2,3,0,1]),
        ('TL-BL-TR-BR', [0,2,1,3]), ('BR-BL-TR-TL', [3,2,1,0]),
    ]
    for name, idx in orders:
        def make_b3(i1,i2,i3,i4):
            return lambda tl,tr,bl,br: [tl,tr,bl,br][i1]*27 + [tl,tr,bl,br][i2]*9 + [tl,tr,bl,br][i3]*3 + [tl,tr,bl,br][i4]
        hypotheses.append(Hypothesis(f"base3_{name}", "base3", f"base3({name})",
            make_b3(*idx), 5, 8))
        for div in [10, 20, 25, 50, 100]:
            def make_b3_div(i1,i2,i3,i4,d):
                return lambda tl,tr,bl,br: ([tl,tr,bl,br][i1]*27 + [tl,tr,bl,br][i2]*9 + [tl,tr,bl,br][i3]*3 + [tl,tr,bl,br][i4]) / d
            hypotheses.append(Hypothesis(f"base3_{name}_div{div}", "base3", f"base3({name})/{div}",
                make_b3_div(*idx, div), 6, 9))

    # KNOWN CANDIDATES
    hypotheses.append(Hypothesis("exact_linear", "linear",
        "(39/50)*TL + (23/100)*TR + (9/100)*BL - 11/100",
        lambda tl,tr,bl,br: (39/50)*tl + (23/100)*tr + (9/100)*bl - 11/100,
        8, 9))
    hypotheses.append(Hypothesis("simple_rational", "rational", "(3*TL + TR) / 4",
        lambda tl,tr,bl,br: (3*tl + tr) / 4, 4, 5))
    hypotheses.append(Hypothesis("candidate_2", "rational", "(TL + BL/2) / 2",
        lambda tl,tr,bl,br: (tl + bl/2) / 2, 4, 5))
    hypotheses.append(Hypothesis("bilinear", "interaction", "(1+TL)*(1+BL)/10",
        lambda tl,tr,bl,br: (1+tl)*(1+bl)/10, 5, 6))

    return hypotheses

# ------------------------------------------------------------------
# EVALUATE
# ------------------------------------------------------------------

def evaluate_catalog(hypotheses: List[Hypothesis], data: Dict, config: Dict) -> List[Hypothesis]:
    n_known = sum(1 for info in data.values() if info['value'] is not None)

    for h in hypotheses:
        preds = {}
        residuals = []
        for sym, info in data.items():
            tl, tr, bl, br = info['corners']
            pred = h.evaluate((tl, tr, bl, br))
            preds[sym] = pred
            if info['value'] is not None:
                residuals.append(pred - info['value'])

        mse = sum(r**2 for r in residuals) / len(residuals) if residuals else 1e12
        h.mse = mse
        h.sigma = math.sqrt(max(mse, 1e-10))
        h.score = bayesian_score(mse, h.complexity, h.node_count, n_known, config)
        h.predictions = preds

    hypotheses.sort(key=lambda x: x.score, reverse=True)
    return hypotheses

# ------------------------------------------------------------------
# PARETO FRONT
# ------------------------------------------------------------------

def compute_pareto(hypotheses: List[Hypothesis]) -> List[Hypothesis]:
    pareto = []
    for h in hypotheses:
        dominated = False
        for other in hypotheses:
            if other.mse <= h.mse and other.complexity <= h.complexity:
                if other.mse < h.mse or other.complexity < h.complexity:
                    dominated = True
                    break
        if not dominated:
            pareto.append(h)
    pareto.sort(key=lambda x: x.complexity)
    return pareto

# ------------------------------------------------------------------
# PREDICT ALL UNKNOWN SYMBOLS
# ------------------------------------------------------------------

def predict_all(hypotheses: List[Hypothesis], pareto: List[Hypothesis], data: Dict) -> Dict:
    unknown_symbols = [s for s, info in data.items() if info['value'] is None]
    results = {}

    print("\n" + "="*70)
    print("PREDICTIONS FOR ALL UNKNOWN SYMBOLS")
    print("="*70)

    for target_sym in sorted(unknown_symbols):
        target_corners = data[target_sym]['corners']
        all_preds = []

        for h in pareto[:8]:
            p = h.evaluate(target_corners)
            if abs(p) < 1e6 and not math.isnan(p):
                all_preds.append(p)

        if not all_preds:
            continue

        mean_pred = sum(all_preds) / len(all_preds)
        var_pred = sum((p - mean_pred)**2 for p in all_preds) / len(all_preds) if len(all_preds) > 1 else 0

        # Abstention
        known_vars = []
        for sym, info in data.items():
            if info['value'] is not None:
                sym_preds = [h.evaluate(info['corners']) for h in pareto[:8]]
                if len(sym_preds) > 1:
                    v = sum((p - sum(sym_preds)/len(sym_preds))**2 for p in sym_preds) / len(sym_preds)
                    known_vars.append(v)

        threshold = sorted(known_vars)[int(len(known_vars)*0.95)] if len(known_vars) >= 5 else max(known_vars)*2 if known_vars else 0.1
        abstained = var_pred > threshold

        status = "ABSTAIN" if abstained else "COMMIT"
        print(f"\n{target_sym} (corners {target_corners}):")
        print(f"  Mean: {mean_pred:.4f} | Variance: {var_pred:.6f} | {status}")

        results[target_sym] = {
            'corners': target_corners,
            'ensemble_mean': round(mean_pred, 4),
            'ensemble_variance': round(var_pred, 6),
            'abstained': abstained,
            'pareto_predictions': {h.name: round(h.evaluate(target_corners), 4) for h in pareto[:5]},
        }

    return results

# ------------------------------------------------------------------
# SAVE
# ------------------------------------------------------------------

def save_results(results: Dict, hypotheses: List[Hypothesis], pareto: List[Hypothesis],
                 data: Dict, config: Dict, filepath: str):
    output = {
        "timestamp": datetime.now().isoformat(),
        "configuration": config,
        "data": {k: {"corners": v['corners'], "value": v['value']} for k, v in data.items()},
        "predictions": results,
        "top_15_models": [
            {
                "rank": i+1,
                "name": h.name,
                "category": h.category,
                "formula": h.formula_str,
                "mse": round(h.mse, 8),
                "score": round(h.score, 4),
                "complexity": h.complexity,
            }
            for i, h in enumerate(hypotheses[:15])
        ],
        "pareto_front": [
            {
                "name": h.name,
                "category": h.category,
                "formula": h.formula_str,
                "mse": round(h.mse, 8),
                "score": round(h.score, 4),
                "complexity": h.complexity,
            }
            for h in pareto[:10]
        ],
    }
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n[Saved] Results written to: {filepath}")

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

def main():
    print("="*70)
    print("MASSIVE 26x4 CORNER-MARK DECODER")
    print("="*70)
    known = sum(1 for v in DATA.values() if v['value'] is not None)
    unknown = sum(1 for v in DATA.values() if v['value'] is None)
    print(f"Known symbols: {known}")
    print(f"Unknown symbols: {unknown}")
    print("="*70)

    print("\nBuilding hypothesis catalog...")
    catalog = build_catalog()
    print(f"Generated {len(catalog)} hypotheses")

    print("\nEvaluating...")
    ranked = evaluate_catalog(catalog, DATA, CONFIG)

    print(f"\nTop 10 models:")
    print("-" * 70)
    for i, h in enumerate(ranked[:10]):
        marker = " ***" if h.mse < 1e-6 else ""
        print(f"{i+1:2d}. {h.name:25s} {h.category:12s} mse={h.mse:.8f} score={h.score:.2f} cplx={h.complexity}{marker}")

    pareto = compute_pareto(ranked)
    print(f"\nPareto front ({len(pareto)} models):")
    for h in pareto[:8]:
        marker = " ***" if h.mse < 1e-6 else ""
        print(f"  {h.name:25s} mse={h.mse:.8f} cplx={h.complexity}{marker}")

    results = predict_all(ranked, pareto, DATA)

    output_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
    output_path = os.path.join(output_dir, 'massive_decoder_results.json')
    save_results(results, ranked, pareto, DATA, CONFIG, output_path)

    print("\n" + "="*70)
    print("NEXT STEP:")
    print("  Edit the DATA dictionary at the top of this script.")
    print("  Change any 'value': None to 'value': YOUR_NUMBER")
    print("  Run again: python massive_decoder.py")
    print("="*70)

if __name__ == '__main__':
    main()
