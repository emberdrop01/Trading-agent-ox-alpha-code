import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from strategy import ema, find_fvg

def make_chart(df, symbol, tf, verdict):
    """Candlestick-style chart with EMAs + FVG zones, returned as PNG bytes."""
    d = df.tail(150).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
    for i, row in d.iterrows():
        color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'
        ax.plot([i, i], [row['low'], row['high']], color=color, lw=0.8)
        ax.add_patch(plt.Rectangle((i - 0.35, min(row['open'], row['close'])),
                     0.7, abs(row['close'] - row['open']) or 1e-9,
                     facecolor=color, edgecolor=color))
    ax.plot(ema(d, 50), color='orange', lw=1.2, label='EMA 50')
    ax.plot(ema(d, 200).tail(150).reset_index(drop=True), color='purple', lw=1.2, label='EMA 200')

    # shade recent FVG zones
    for lo, hi, t, i in find_fvg(d)[-8:]:
        ax.axhspan(lo, hi, color='green' if t == 'bull' else 'red', alpha=0.12)

    ax.set_title(f"{symbol} {tf} — Signal: {verdict}")
    ax.legend(loc='upper left')
    ax.grid(alpha=0.2)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def send_telegram_photo(buf, caption):
    import os, requests
    tok, chat = os.environ['TELEGRAM_TOKEN'], os.environ['TELEGRAM_CHAT_ID']
    requests.post(f"https://api.telegram.org/bot{tok}/sendPhoto",
                  data={'chat_id': chat, 'caption': caption},
                  files={'photo': ('chart.png', buf)})
