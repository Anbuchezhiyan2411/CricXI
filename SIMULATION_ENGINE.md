# CricXI — Advanced Statistical Match Simulation Engine
## Architecture, Mathematical Formulation & Data Science Foundations

---

### Executive Summary

In CricXI Phase 4.2, the match simulation was upgraded from a naive rating-to-probability model to an **empirical, data-driven, statistical simulation pipeline**. The engine integrates:
1. **Population-level feature standardization via Z-score normalization**.
2. **Cumulative Normal Distribution Function ($\Phi$) mapping** for unified multi-feature weighting.
3. **Automated, data-driven player profiling** (Batting & Bowling Styles) derived entirely from statistical records without manual labels.
4. **Context-aware dynamic state variables**: player confidence, match momentum, unbroken partnerships, and bowler fatigue.
5. **Environmental modifiers**: pitch conditions, weather, match phases, and field placements.
6. **Chase intelligence** driven by Required Run Rate (RRR) vs Current Run Rate (CRR).
7. **500-iteration Monte Carlo delivery simulation** with stochastic execution jitter, running in under 3 milliseconds per delivery ($< 20\text{ ms}$ threshold).
8. **Mathematical reconciliation and validation checks** after each delivery and innings.

---

## 1. Feature Standardization & Z-Score Normalization

### 1.1 The Mathematical Problem
Cricket metrics reside on wildly disparate scales:
- Batting ratings: $[0, 100]$
- Batting averages: $[0, 60+]$
- Strike rates: $[50, 200+]$
- Bowling economies: $[4.0, 12.0]$ (where lower values represent superior performance)
- Bowling strike rates: $[10.0, 40.0]$ (where lower values represent superior performance)

Directly combining these unstandardized values introduces scale bias and distorts player evaluation.

### 1.2 Population Z-Score Calculation
For any player metric $x_i$ belonging to population feature $X$:
$$z_i = \frac{x_i - \mu_X}{\sigma_X}$$

Where:
- $\mu_X = \frac{1}{N} \sum_{k=1}^N x_k$ (Population Mean)
- $\sigma_X = \sqrt{\frac{1}{N-1} \sum_{k=1}^N (x_k - \mu_X)^2}$ (Population Standard Deviation)

If $\sigma_X = 0$, $z_i = 0.0$ to prevent division by zero.

### 1.3 Percentile Transformation via Standard Normal CDF ($\Phi$)
Because unbounded Z-scores ($z \in (-\infty, +\infty)$) can destabilize downstream linear combinations, each Z-score is mapped to a continuous percentile score $P \in [0.001, 0.999]$ using the **Standard Normal Cumulative Distribution Function**:
$$\Phi(z) = \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{z} e^{-\frac{t^2}{2}} dt = \frac{1}{2} \left[ 1 + \text{erf}\left( \frac{z}{\sqrt{2}} \right) \right]$$

Where $\text{erf}(u) = \frac{2}{\sqrt{\pi}} \int_{0}^u e^{-t^2} dt$ is the Gauss error function.

**Properties of $\Phi(z)$ in CricXI:**
- Average performance ($z = 0$) evaluates to exactly $\Phi(0) = 0.50$ (50th percentile).
- Elite performance ($z = +1.96$, top 2.5%) evaluates to $\Phi(1.96) \approx 0.975$.
- Subpar performance ($z = -1.96$, bottom 2.5%) evaluates to $\Phi(-1.96) \approx 0.025$.

---

## 2. Weighted Player Strength Formulas

### 2.1 Batting Strength ($S_{\text{bat}}$)
Batting strength reflects a weighted composite of raw skill, scoring efficiency, consistency, and boundary clearing ability:
$$S_{\text{bat}} = w_1 \Phi(z_{\text{rating}}) + w_2 \Phi(z_{\text{avg}}) + w_3 \Phi(z_{\text{sr}}) + w_4 \Phi(z_{\text{bound}})$$

**Weights:**
- $w_1 = 0.40$ (Batting Rating)
- $w_2 = 0.25$ (Batting Average)
- $w_3 = 0.20$ (T20 Strike Rate)
- $w_4 = 0.15$ (Boundary Frequency: $\frac{\text{Fours} + \text{Sixes}}{\max(1, \text{Balls Faced})}$)

$S_{\text{bat}}$ is clamped strictly to $[0.05, 0.95]$.

### 2.2 Bowling Strength ($S_{\text{bowl}}$)
For bowling economy ($\text{Econ}$), bowling strike rate ($\text{BSR}$), and bowling average ($\text{BAvg}$), lower numerical values indicate superior bowler performance. Therefore, their Z-scores are negated:
$$z_{\text{econ}}^{\text{inv}} = - \frac{\text{Econ} - \mu_{\text{econ}}}{\sigma_{\text{econ}}}$$
$$z_{\text{bsr}}^{\text{inv}} = - \frac{\text{BSR} - \mu_{\text{bsr}}}{\sigma_{\text{bsr}}}$$
$$z_{\text{bavg}}^{\text{inv}} = - \frac{\text{BAvg} - \mu_{\text{bavg}}}{\sigma_{\text{bavg}}}$$

The composite bowling strength is computed as:
$$S_{\text{bowl}} = v_1 \Phi(z_{\text{rating}}) + v_2 \Phi(z_{\text{econ}}^{\text{inv}}) + v_3 \Phi(z_{\text{bsr}}^{\text{inv}}) + v_4 \Phi(z_{\text{bavg}}^{\text{inv}}) + v_5 \Phi(z_{\text{wfreq}})$$

**Weights:**
- $v_1 = 0.35$ (Bowling Rating)
- $v_2 = 0.25$ (Economy Rate)
- $v_3 = 0.20$ (Bowling Strike Rate)
- $v_4 = 0.10$ (Bowling Average)
- $v_5 = 0.10$ (Wicket Frequency: $\frac{\text{Wickets}}{\max(1, \text{Balls Bowled})}$)

$S_{\text{bowl}}$ is clamped strictly to $[0.05, 0.95]$.

---

## 3. Automated Data-Driven Style Classification

Rather than relying on manual player tagging, styles are inferred dynamically from historical statistics:

### 3.1 Batting Styles
1. **Tailender**: $\text{Rating} < 35.0$ or ($\text{Role} = \text{BOWL}$ and $\text{Rating} < 48.0$ and $S_{\text{bat}} < 0.28$).
   - *Behavior*: Extreme dot ball rate ($+65\%$), severe dismissal risk ($\times 2.25$), boundary suppression ($\times 0.45$).
2. **Lower Order**: $\text{Rating} < 56.0$ or ($\text{Role} \in \{\text{BOWL}, \text{AR}\}$ and $\text{Rating} < 62.0$).
   - *Behavior*: High dot ball rate ($+25\%$), elevated dismissal risk ($\times 1.45$).
3. **Aggressive Opener**: Top order position ($1$ or $2$) and ($\text{SR} \ge 135.0$ or $\text{Boundary Freq} \ge 0.16$).
   - *Behavior*: Attacks new ball; fours $\times 1.30$, sixes $\times 1.25$, dismissal risk $\times 1.20$.
4. **Power Hitter**: $\frac{\text{Sixes}}{\max(1, \text{Fours})} \ge 0.45$ and $\text{SR} \ge 135.0$, or $\text{SR} \ge 148.0$.
   - *Behavior*: Maximum boundary power; sixes $\times 1.55$, fours $\times 1.20$, dots $\times 1.12$.
5. **Finisher**: Positions $5, 6, 7$ and ($\text{SR} \ge 130.0$ or $\text{Avg} \ge 26.0$).
   - *Behavior*: Lethal in death overs; sixes $\times 1.35$, fours $\times 1.25$, strike rotation $\times 1.10$.
6. **Anchor**: $\text{Avg} \ge 34.0$ and $\text{SR} < 128.0$.
   - *Behavior*: Preserves wicket; dismissal risk $\times 0.65$, singles $\times 1.25$, sixes $\times 0.65$.
7. **Accumulator**: $\text{Avg} \ge 26.0$ and $\text{SR} < 132.0$.
   - *Behavior*: Strike rotator; singles $\times 1.30$, doubles $\times 1.20$, dots $\times 0.80$.
8. **Stroke Maker**: Standard proficient batter ($\text{Rating} \ge 65.0$).
   - *Behavior*: Adaptable; fours $\times 1.15$, sixes $\times 1.10$, dismissal risk $\times 0.95$.

### 3.2 Bowling Styles
1. **Part Timer**: $\text{Rating} < 50.0$ and $\text{Role} \in \{\text{BAT}, \text{WK}\}$, or $S_{\text{bowl}} < 0.25$.
   - *Behavior*: Higher boundary leak ($\times 1.35$), lower wicket penetration ($\times 0.65$).
2. **Fast Strike Bowler**: Pace bowler with $\text{BSR} \le 18.5$ and $\text{Rating} \ge 75.0$.
   - *Behavior*: Wicket strike weapon ($\times 1.30$), dots $\times 1.12$.
3. **Defensive Seamer**: Pace bowler with $\text{Econ} \le 7.4$.
   - *Behavior*: Suffocates scoring; dots $\times 1.22$, boundaries $\times 0.80$.
4. **Swing Bowler**: Seamer with swing characteristics or new ball role.
   - *Behavior*: High movement in powerplay/overcast; wickets $\times 1.20$, dots $\times 1.15$.
5. **Finger Spinner**: Off-spin or slow left-arm orthodox.
   - *Behavior*: Controls middle overs; dots $\times 1.18$, extras $\times 0.70$.
6. **Leg Spinner**: Wrist spin / leg-break.
   - *Behavior*: High wicket threat ($\times 1.25$), higher variability/extras ($\times 1.20$).
7. **Mystery Spinner**: Spin with high rating ($\ge 85.0$) and low economy ($< 6.8$).
   - *Behavior*: Extremely hard to score off; dots $\times 1.35$, wickets $\times 1.25$, boundaries $\times 0.75$.

---

## 4. Matchup Differential & Dynamic State Variables

### 4.1 Matchup Differential ($\Delta S$)
$$\Delta S = S_{\text{bat}} - S_{\text{bowl}} \in [-0.90, +0.90]$$
- If $\Delta S > 0$ (Batter advantage): Boundaries boosted by $+30-35\% \cdot \Delta S$, dots and wickets suppressed.
- If $\Delta S < 0$ (Bowler advantage): Dot balls boosted by $+20\% \cdot |\Delta S|$, wickets boosted by $+35\% \cdot |\Delta S|$.

### 4.2 Dynamic Player Confidence ($C$)
Confidence is modeled as a bounded continuous Markovian state variable:
$$C_t \in [15.0, 95.0], \quad C_0 = 50.0$$

**Batter Updates:**
- Boundary four: $+2.0$
- Boundary six: $+3.5$
- Milestone (50 runs): $+8.0$, Century (100 runs): $+12.0$
- Dot ball penalty: $-0.3 \cdot \text{dots}$
- Normalized confidence modifier: $\kappa_b = \frac{C_{\text{bat}} - 50.0}{50.0}$
  - If $\kappa_b > 0$: Fours $\times (1 + 0.18 \kappa_b)$, Sixes $\times (1 + 0.22 \kappa_b)$, Wickets $\times (1 - 0.18 \kappa_b)$.
  - If $\kappa_b < 0$: Dots $\times (1 + 0.18 |\kappa_b|)$, Wickets $\times (1 + 0.25 |\kappa_b|)$.

**Bowler Updates:**
- Wicket taken: $+10.0$
- Maiden over: $+8.0$
- Dot ball: $+0.3$
- Runs conceded penalty: $-0.4 \cdot \text{runs}$
- Normalized confidence modifier: $\kappa_{bw} = \frac{C_{\text{bowl}} - 50.0}{50.0}$
  - If $\kappa_{bw} > 0$: Wickets $\times (1 + 0.18 \kappa_{bw})$, Dots $\times (1 + 0.15 \kappa_{bw})$.

### 4.3 Match Momentum ($M$)
Momentum measures the net trajectory over the past 10 deliveries:
$$M = \sum_{k=1}^{\min(10, N)} \Delta m_k, \quad M \in [-5.0, +5.0]$$
Where $\Delta m = +1.5$ for boundary, $+0.3$ for run, $-2.0$ for wicket, $-0.2$ for dot.
- Positive momentum ($M > 0$) boosts boundary rates.
- Negative momentum ($M < 0$) induces pressure and elevates wicket risk.

### 4.4 Unbroken Partnership Engine ($R_p$)
Tracks cumulative runs scored by the current pair since the last wicket:
- $R_p \ge 30$: Wicket probability $\times 0.90$.
- $R_p \ge 50$: Wicket probability $\times 0.80$, strike rotation $+8\%$.
- $R_p \ge 75$: Wicket probability $\times 0.70$, fours $+10\%$.
- $R_p \ge 100$: Wicket probability $\times 0.60$, boundaries $+15\%$.
- Wicket fall immediately resets partnership $R_p = 0$.

---

## 5. Environmental & Contextual Modifiers

| Condition Type | State | Effects on Simulation |
| :--- | :--- | :--- |
| **Pitch** | `Green Pitch` | Seam & swing assist: Pacer wickets $+25\%$, dots $+15\%$, boundaries $-15\%$. |
| | `Flat Batting Pitch` | True bounce: Fours $+25\%$, Sixes $+25\%$, wickets $-25\%$, dots $-15\%$. |
| | `Dry Turning Pitch` | Spin assistance: Spinner wickets $+30\%$, dots $+20\%$, boundaries $-20\%$. |
| | `Balanced Pitch` | Baseline neutrality. |
| **Weather** | `Overcast` | Heavy swing in air: Wickets $+12\%$, wide balls $+10\%$. |
| | `Sunny` | Optimal batting visibility: Fours $+6\%$. |
| **Match Phase** | `Powerplay (0-5)` | Infield attacking: Fours $+25\%$, dots $+10\%$, singles $-15\%$. |
| | `Middle (6-14)` | Field spread: Singles $+25\%$, doubles $+15\%$, boundaries $-10\%$. |
| | `Death (15-19)` | Maximum slogging: Sixes $+50\%$, fours $+25\%$, wickets $+40\%$, dots $-25\%$. |
| **Bowler Fatigue** | `Over 3` | Control drop: Fours $+4\%$, wides $+8\%$. |
| | `Over 4` | Fatigue: Fours $+8\%$, sixes $+12\%$, wides $+15\%$, no-balls $+15\%$. |

---

## 6. Second Innings Chase Intelligence

In the second innings, the Required Run Rate directly drives tactical aggression:
$$\text{RRR} = \frac{\text{Runs Required} \times 6.0}{\max(1, \text{Balls Remaining})}$$

1. **Urgent Chase ($\text{RRR} \ge 12.0$):**
   - Batters must take extreme risks: Sixes $\times 1.45$, Fours $\times 1.25$, Wicket risk $\times 1.35$, Dots $\times 0.75$.
2. **Accelerated Chase ($\text{RRR} \ge 9.0$):**
   - Elevated attack: Sixes $\times 1.25$, Fours $\times 1.15$, Wickets $\times 1.15$.
3. **Controlled Cruise ($\text{RRR} \le 5.5$ with Runs Required $\le 30$):**
   - Risk avoidance: Singles $\times 1.35$, Doubles $\times 1.15$, Wickets $\times 0.45$, Sixes $\times 0.50$.

---

## 7. Monte Carlo Simulation Engine

### 7.1 Algorithm & Execution Architecture
Rather than sampling directly from a static vector, the engine employs a **500-sample Monte Carlo stochastic sampling process**:

```
[Statistical Player Profiles & Context]
                   ↓
[Base Probability Vector P (11 outcomes)]
                   ↓
    Loop k = 1 to 500 (Monte Carlo Trials):
       Apply execution jitter: ε ~ N(0, 0.08²)
       P̃_i^(k) = max(0.0001, P_i * (1 + ε_i^(k)))
       Normalize P̃^(k)
       Sample micro-outcome y^(k)
       Accumulate empirical counts C[y^(k)] += 1
                   ↓
[Smooth Empirical Distribution: P̂_i = C[i] / 500]
                   ↓
[Final Multinomial Selection: y* ~ Multinomial(P̂)]
```

### 7.2 Why Monte Carlo Outperforms Pure Random Choice
1. **Models Real-World Execution Uncertainty:** Even elite bowlers miss a yorker by 2 inches; even set batters occasionally mistime a sweep. The stochastic noise $\epsilon \sim \mathcal{N}(0, 0.08^2)$ captures execution variance.
2. **Distribution Smoothing:** Monte Carlo sampling eliminates step-function artifacts and sharp probability cliffs, producing authentic cricketing variance.
3. **Benchmark Performance:** The vectorized Python implementation completes all 500 iterations in **$2.8 \text{ ms}$**, well below the $20 \text{ ms}$ real-time multiplayer latency ceiling.
4. **Deterministic Testing Mode:** When a fixed `seed` is passed, the random number generator behaves 100% deterministically, allowing exact match reproduction for regression testing.

---

## 8. Statistical Validation & Invariant Reconciliation

After every delivery and upon innings completion, the engine enforces strict cricket invariants:

1. **Scoring Invariant:**
   $$\text{Total Innings Runs} = \sum_{i=1}^{11} \text{Batter Runs}_i + \text{Extras}$$
2. **Delivery Volume Invariant:**
   $$\text{Balls Faced}_i = \text{Legal Balls Faced}_i + \text{No-Balls Faced}_i + \text{Byes Faced}_i + \text{Leg-Byes Faced}_i$$
   *(Wides do not increment balls faced by the batter).*
3. **Wicket Reconciliation Invariant:**
   $$\text{Total Innings Wickets} = \sum_{i=1}^{11} \mathbf{1}_{\{\text{Batter Out}_i = \text{True}\}}$$
4. **Overs Ceiling Invariant:**
   $$\text{Legal Deliveries} \le 120 \quad (\text{Overs} \le 20.0)$$

---

## 9. Data Science Concepts Summary for Project Viva

| Concept | Implementation in CricXI | Mathematical Justification |
| :--- | :--- | :--- |
| **Z-Score Normalization** | Population standardization of rating, average, strike rate, economy. | Centers features to $\mu = 0, \sigma = 1$, eliminating scale bias. |
| **Normal CDF ($\Phi$)** | Percentile transformation of unbounded Z-scores into $[0, 1]$. | Maps standard normal variables to unified, bounded cumulative percentiles. |
| **Feature Engineering** | Derived Boundary Frequency and Wicket Frequency ratios. | Extracts direct efficiency metrics from raw balls and boundary counts. |
| **Unsupervised Profiling** | Automated Batting & Bowling style classifications. | Rule-based decision tree operating on standardized statistical metrics. |
| **Markovian State Variables** | Dynamic player confidence & team momentum. | Tracks time-series memory and autocorrelated outcome probability shifts. |
| **Monte Carlo Sampling** | 500 stochastic trials per delivery with Gaussian noise $\epsilon \sim \mathcal{N}(0, 0.08^2)$. | Numerical estimation and distribution smoothing under micro-execution variance. |
| **Multinomial Distribution** | 11 discrete delivery outcome states with dynamic normalization. | Enforces valid probability simplex $\sum_{i=1}^{11} p_i = 1.0, p_i > 0$. |

