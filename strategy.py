import pandas as pd
import numpy as np

def ema(df, span):
    return df['close'].ewm(span=span, adjust=False).mean()

def find_fvg(df):
    """Fair Value Gaps: 3-candle imbalance. Returns list of (lo, hi, type)."""
    gaps = []
    for i in range(2, len(df)):
        c1, c3 = df.iloc[i-2], df.iloc[i]
        if c3['low'] > c1['high']:   # bullish gap
            gaps.append((c1['high'], c3['low'], 'bull', i))
        elif c3['high'] < c1['low']: # bearish gap
            gaps.append((c3['high'], c1['low'], 'bear', i))
    return gaps

def fvg_retest(df, lookback=200):
    """Is price currently retesting a recent FVG?"""
    gaps = [g for g in find_fvg(df.tail(lookback)) if g[3] >= len(df) - lookback]
    price = df['close'].iloc[-1]
    hit = None
    for lo, hi, t, i in gaps[-20:]:
        if lo <= price <= hi:
            hit = {'type': t, 'lo': lo, 'hi': hi}
    return hit

def golden_cross(df):
    e50, e200 = ema(df, 50), ema(df, 200)
    if len(df) < 205: return "insufficient"
    a, b = e50.iloc[-1], e200.iloc[-1]
    pa, pb = e50.iloc[-2], e200.iloc[-2]
    if pa <= pb and a > b: return "GOLDEN_CROSS"
    if pa >= pb and a < b: return "DEATH_CROSS"
    return "BULL_TREND" if a > b else "BEAR_TREND"

def candle_patterns(df):
    """Detects common reversal candles on the last bar."""
    o, h, l, c = (df[k].iloc[-1] for k in ['open','high','low','close'])
    po, pc = df['open'].iloc[-2], df['close'].iloc[-2]
    body, rng = abs(c-o), h-l
    out = []
    if body / rng < 0.1 and rng > 0: out.append("Doji")
    if c > o and (min(o,c)-l) > 2*body: out.append("Hammer")
    if c < o and (h-max(o,c)) > 2*body: out.append("Shooting_Star")
    if c > o and pc < po and c >= po and o <= pc: out.append("Bullish_Engulfing")
    if c < o and pc > po and o >= pc and c <= po: out.append("Bearish_Engulfing")
    return out

def trend(df):
    e50, e200 = ema(df, 50), ema(df, 200)
    if e50.iloc[-1] > e200.iloc[-1]: return "BULLISH"
    return "BEARISH"

def analyze(df):
    """Full confluence score. +1 = bullish factor, -1 = bearish."""
    score, reasons = 0, []
    fvg = fvg_retest(df)
    t = trend(df); gc = golden_cross(df)
    pats = candle_patterns(df)

    if fvg:
        if fvg['type'] == 'bull' and t == "BULLISH":
            score += 2; reasons.append(f"Price retesting BULLISH FVG {fvg['lo']:.5f}-{fvg['hi']:.5f} with trend")
        elif fvg['type'] == 'bear' and t == "BEARISH":
            score -= 2; reasons.append(f"Price retesting BEARISH FVG {fvg['lo']:.5f}-{fvg['hi']:.5f} with trend")
    if gc == "GOLDEN_CROSS":
        score += 2; reasons.append("GOLDEN CROSS 50/200 EMA (fresh)")
    elif gc == "DEATH_CROSS":
        score -= 2; reasons.append("DEATH CROSS 50/200 EMA (fresh)")
    if t == "BULLISH": score += 1; reasons.append("Bullish 50>200 EMA trend")
    else: score -= 1; reasons.append("Bearish 50<200 EMA trend")

    bullish_p = {'Hammer','Bullish_Engulfing'}
    for p in pats:
        if p in bullish_p: score += 1; reasons.append(f"Candle: {p}")
        else: score -= 1; reasons.append(f"Candle: {p}")
    return score, reasons, fvg
def confidence(score, reasons, bt, n_candles):
    """0-100 confidence combining confluence, backtest quality, sample size."""
    # base: confluence strength (score can range roughly -7..+7)
    base = min(abs(score) / 7, 1) * 40          # up to 40 pts

    # backtest quality: win rate above/below breakeven for 1.5R
    wr_pts = 0
    if bt and bt.get('signals', 0) > 0:
        wr = bt['win_rate_%']
        # 50% WR at 1.5R ≈ breakeven-ish; scale 40→85%
        wr_pts = max(0, min((wr - 45) / 40, 1)) * 35   # up to 35 pts

    # sample size: more historical signals = more trustworthy
    n_pts = 0
    if bt:
        n_pts = min(bt['signals'] / 30, 1) * 15        # up to 15 pts

    # data depth: 500+ candles required for full trust
    depth_pts = min(n_candles / 600, 1) * 10           # up to 10 pts

    # confluence diversity: more agreeing factors = more robust
    div_pts = min(len(reasons) / 6, 1) * 5             # up to 5 pts  → total 105, cap 100

    return round(min(base + wr_pts + n_pts + depth_pts + div_pts, 100))


