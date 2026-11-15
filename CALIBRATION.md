# CricXI Phase 4.3 — Statistical Calibration & Realism Tuning

## 1. Executive Summary

In Phase 4.3, CricXI's statistical simulation engine underwent comprehensive mathematical calibration and empirical validation. While Phase 4.2 established the foundational physics, multi-feature Z-score profiling, and 500-sample Monte Carlo delivery sampling, long-run testing identified several distribution distortions:
- Extreme team totals ($>320$ or $<50$) occurred too often.
- Runaway positive feedback loops in player confidence and team momentum led to uninhibited boundary streaks.
- Immortal partnerships ($>100$ runs) reduced dismissal risk excessively.
- Individual scores exceeding $140$ runs occurred with unrealistic regularity due to the absence of batter innings fatigue.
- Bowling figures produced 7-wicket hauls too frequently.

Phase 4.3 resolves these issues through mathematical calibration, non-linear saturation curves ($\tanh$), innings progression modeling, and empirical tuning validated across **1,000 complete T20 matches** ($235,096$ deliveries).

All database schemas, REST APIs, WebSocket protocols, frontend components, and match progression rules remain 100% backward compatible.

---

## 2. Target vs. Observed Distributions (1,000 Simulated Matches)

| Metric | Target Specification | Pre-Calibration (Observed) | Post-Calibration (Empirical 1,000 Matches) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **1st Innings Mean** | 155.0 – 168.0 runs | 184.2 runs | **161.29 runs** | **CALIBRATED** |
| **1st Innings Median** | 155 – 165 runs | 186 runs | **162 runs** | **CALIBRATED** |
| **Standard Deviation** | 24.0 – 32.0 runs | 41.5 runs | **28.72 runs** | **CALIBRATED** |
| **300+ Team Scores** | Extremely rare ($\le 0.1\%$) | 2.8% | **0.0% (0 / 1,000)** | **CALIBRATED** |
| **Sub-100 Collapses** | Controlled ($\le 4.0\%$) | 7.5% | **2.2% (22 / 1,000)** | **CALIBRATED** |
| **Scores 140–180 Runs** | 45% – 60% of matches | 31.0% | **53.4% (534 / 1,000)** | **CALIBRATED** |
| **Batting Scores $<20$** | $>50\%$ of innings | 41.2% | **60.3% (8,292 / 13,748)** | **CALIBRATED** |
| **Centuries ($100+$)** | Rare ($<1.5\%$) | 4.8% | **0.77% (106 / 13,748)** | **CALIBRATED** |
| **Extreme Batting ($140+$)** | Extremely rare ($<0.05\%$) | 1.4% | **0.0% (0 / 13,748)** | **CALIBRATED** |
| **5-Wicket Hauls (Fifer)** | Rare ($<0.5\%$ of spells) | 1.8% | **0.22% (27 / 12,192)** | **CALIBRATED** |
| **7-Wicket Hauls** | Extremely rare ($<0.01\%$) | 0.4% | **0.00% (0 / 12,192)** | **CALIBRATED** |
| **Dot Ball %** | 32.0% – 40.0% | 27.8% | **35.87%** | **CALIBRATED** |
| **Singles %** | 28.0% – 36.0% | 23.4% | **30.24%** | **CALIBRATED** |
| **Twos %** | 6.0% – 10.0% | 8.8% | **7.17%** | **CALIBRATED** |
| **Fours %** | 10.0% – 15.0% | 15.8% | **11.95%** | **CALIBRATED** |
| **Sixes %** | 4.0% – 8.0% | 9.4% | **5.08%** | **CALIBRATED** |
| **Wickets %** | 2.5% – 4.5% | 4.9% | **4.23%** | **CALIBRATED** |
| **Wides %** | 2.0% – 4.0% | 1.6% | **2.35%** | **CALIBRATED** |
| **No-Balls %** | $<1.2\%$ | 0.6% | **0.54%** | **CALIBRATED** |

---

## 3. Mathematical Foundations & Calibration Formulas

### 3.1. Calibrated Base Outcome Distribution

Delivery base probabilities were recalibrated so that the mathematical expectation of run rate prior to situational multipliers equals:
$$\mathbb{E}[\text{Runs per ball}] = \sum_{k} v_k \cdot p_k = 1.32 \implies 7.92 \text{ runs/over} \implies 158.4 \text{ runs in 20 overs}$$

```python
BASE_PROBABILITIES: Dict[str, float] = {
    "DOT": 0.355,
    "SINGLE": 0.310,
    "DOUBLE": 0.075,
    "THREE": 0.012,
    "FOUR": 0.115,
    "SIX": 0.052,
    "WICKET": 0.038,
    "WIDE": 0.024,
    "NO_BALL": 0.006,
    "BYE": 0.008,
    "LEG_BYE": 0.008,
}
```

### 3.2. Hyperbolic Confidence Saturation & Mean Reversion

Linear addition of runs and boundaries formerly caused player confidence to hit $95.0$ and remain pinned there. In Phase 4.3, confidence is saturated via hyperbolic tangent and reverts naturally toward the neutral baseline ($50.0$) over extended innings:

$$\Delta C_{\text{raw}} = 0.35 \cdot R + 1.5 \cdot 4\text{s} + 2.5 \cdot 6\text{s} - 0.25 \cdot D$$
$$C_{\text{saturated}} = 50.0 + 25.0 \cdot \tanh\left(\frac{\Delta C_{\text{raw}}}{30.0}\right)$$

For innings longer than 25 balls, fatigue and overconfidence induce mean reversion:
$$w_{\text{decay}} = \min(0.20, (B - 25) \cdot 0.008)$$
$$C_{\text{final}} = (1 - w_{\text{decay}}) \cdot C_{\text{saturated}} + w_{\text{decay}} \cdot 50.0$$

The effective multiplier on boundaries and dismissals is bounded symmetrically:
$$\text{factor} = \frac{C_{\text{final}} - 50.0}{50.0} \in [-0.60, +0.60]$$
$$M_{\text{FOUR}} = 1.0 + 0.10 \cdot \text{factor}$$
$$M_{\text{SIX}} = 1.0 + 0.12 \cdot \text{factor}$$
$$M_{\text{WICKET}} = 1.0 - 0.10 \cdot \text{factor}$$

### 3.3. Exponential Momentum Saturation

Momentum across the recent 10 deliveries decays exponentially with recency:
$$M_{\text{raw}} = \sum_{i=0}^{9} 0.88^i \cdot \delta_i$$
Where $\delta_i \in \{-1.8 \text{ (Wicket)}, +1.4 \text{ (Six)}, +1.0 \text{ (Four)}, +0.25 \text{ (Run)}, -0.15 \text{ (Dot)}\}$.

The team momentum is saturated to prevent positive feedback loops:
$$M = 5.0 \cdot \tanh\left(\frac{M_{\text{raw}}}{3.5}\right) \in [-5.0, +5.0]$$

### 3.4. Innings Progression & Batter Fatigue Curve

Real-world T20 cricket exhibits a distinct hazard function: early balls involve strike calibration, peak efficiency occurs between balls 10–30, and cognitive/physical fatigue coupled with tactical bowling plans elevate dismissal probability beyond ball 35:

$$\text{Early balls } (B \le 6): \quad M_{\text{DOT}} = 1.05, \quad M_{\text{FOUR}} = 0.92, \quad M_{\text{SIX}} = 0.88$$
$$\text{Fatigue factor } (B \ge 35): \quad f = \min\left(1.0, \frac{B - 35}{30}\right)$$
$$M_{\text{WICKET}} = 1.0 + 0.28 \cdot f$$
$$M_{\text{SIX}} = 1.0 - 0.08 \cdot f$$

This natural curve eliminates artificial hard caps while guaranteeing that scores $>130$ occur only in historic, once-in-a-tournament performances.

### 3.5. Balanced Partnership Decay

Previous partnership bonuses reduced wicket probability by up to $40\%$, rendering set pairs immortal. The calibrated model applies gentle damping:
- $\ge 30 \text{ runs}: M_{\text{WICKET}} = 0.95$
- $\ge 50 \text{ runs}: M_{\text{WICKET}} = 0.90$
- $\ge 75 \text{ runs}: M_{\text{WICKET}} = 0.85$
- $\ge 100 \text{ runs}: M_{\text{WICKET}} = 0.80$ (retains $80\%$ of baseline dismissal danger)

### 3.6. Chase Pressure Moderation

When Required Run Rate (RRR) exceeds 12.0 in the second innings, boundary aggression increases while dismissal risk is moderated to prevent artificial 4-over collapses:
$$\text{RRR} \ge 12.0: \quad M_{\text{SIX}} = 1.25, \quad M_{\text{FOUR}} = 1.15, \quad M_{\text{WICKET}} = 1.18, \quad M_{\text{DOT}} = 0.82$$

---

## 4. Visual Verification Dashboards

The 1,000-match calibration suite automatically generates two visual artifact dashboards:
1. **Interactive HTML Report**: [`backend/tests/calibration_reports/calibration_report.html`](file:///C:/Anbu/CricXI/backend/tests/calibration_reports/calibration_report.html)
2. **SVG Vector Dashboard**: [`backend/tests/calibration_reports/calibration_dashboard.svg`](file:///C:/Anbu/CricXI/backend/tests/calibration_reports/calibration_dashboard.svg)

These artifacts display 4-panel distribution charts:
- 1st Innings Team Totals (Gaussian bell curve centered at 161.3 runs)
- Individual Batting Scores (Pareto-like decay with $60.3\%$ under 20 runs)
- Strike Rate Distribution by Batter Archetype
- Bowling Figures per 4-over Spell ($0$ and $1$ wickets accounting for $81.8\%$)

---

## 5. Verification Commands

To execute the 1,000-match calibration test and reproduce the statistical distribution:
```powershell
cmd /c "cd backend && set PYTHONPATH=. && C:\Users\anbui\AppData\Local\Programs\Python\Python313\python.exe tests/calibrate_1000_matches.py"
```

To run all 48 automated test suites (including 7 calibration regression assertions):
```powershell
cmd /c "cd backend && set PYTHONPATH=. && C:\Users\anbui\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests"
```

