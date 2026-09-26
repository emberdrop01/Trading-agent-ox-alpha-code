import pandas as pd
import numpy as np
from strategy import analyze

def backtest(df, min_score=3, rr=1.5, sl_pct=0.002):
    """Walk-forward: at every candle, if analyze() score >= min_score,
    simulate a trade: SL = sl_pct, TP = rr*SL. Track outcome."""
    wins = losses = 0
    for i in range(210, len(df) - 20):
        window = df.iloc[:i+1]
        score, _, _ = analyze(window)
        if score >= min_score:
            entry = window['close'].iloc[-1]
            sl, tp = entry*(1-sl_pct), entry*(1+sl_pct*rr)
            future = df.iloc[i+1:i+21]
            hit_sl = (future['low'] <= sl).any()
            hit_tp = (future['high'] >= tp).any()
            if hit_tp and not hit_sl: wins += 1
            elif hit_sl: losses += 1
    total = wins + losses
    wr = wins/total*100 if total else 0
    expectancy = (wr/100*rr) - ((1-wr/100))
    return {'signals': total, 'wins': wins, 'losses': losses,
            'win_rate_%': round(wr,1), 'expectancy_R': round(expectancy,2)}
