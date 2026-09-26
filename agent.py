import os, json, requests, pandas as pd
from datetime import datetime, timezone
import google.generativeai as genai
from strategy import analyze, confidence
from backtest import backtest
from chart import make_chart, send_telegram_photo

def fetch_twelvedata(symbol, tf, key):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={tf}&outputsize=600&apikey={key}"
    d = requests.get(url).json()
    df = pd.DataFrame(d['values'][::-1]).astype(float)
    df.columns = ['datetime','open','high','low','close','volume']
    return df

def fetch_binance(symbol, tf):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={tf}&limit=600"
    raw = requests.get(url).json()
    df = pd.DataFrame(raw, columns=['t','open','high','low','close','volume','ct','qv','n','qb','qc','ig'])
    for c in ['open','high','low','close','volume']: df[c] = df[c].astype(float)
    return df

def send_telegram(msg):
    tok, chat = os.environ['TELEGRAM_TOKEN'], os.environ['TELEGRAM_CHAT_ID']
    requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                  json={'chat_id': chat, 'text': msg, 'parse_mode': 'Markdown'})

from ai_provider import ask_ai

def ai_opinion(symbol, tf, score, reasons, bt, conf):
    prompt = (f"You are a strict technical analyst. Symbol {symbol} timeframe {tf}. "
              f"Confluence score {score}, confidence {conf}/100. Signals: {reasons}. "
              f"Backtest on 500+ candles: {json.dumps(bt)}. "
              f"Give a 3-line opinion: bias (BUY/SELL/WAIT), key levels to watch, risk note. "
              f"Opinion only, not financial advice.")
    return ask_ai(prompt)


def run():
    cfg = json.load(open('config.json'))
    td_key = os.environ.get('TWELVEDATA_KEY', '')
    rows = []
    for sym in cfg['symbols']:
        for tf in cfg['timeframes']:
            try:
                df = fetch_twelvedata(sym, tf, td_key) if td_key and '/' in sym and 'USDT' not in sym \
                     else fetch_binance(sym.replace('/', ''), tf)
                if len(df) < 250: continue
                score, reasons, fvg = analyze(df)
                conf = confidence(score, reasons, backtest(df), len(df))
                bt = backtest(df) if abs(score) >= cfg['min_score_to_alert'] else {}
                verdict = "BUY" if score >= 3 else "SELL" if score <= -3 else "WAIT"
                ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
                rows.append({'time': ts, 'symbol': sym, 'tf': tf, 'verdict': verdict,
                             'score': score, 'confidence': conf,
                             'win_rate': bt.get('win_rate_%', ''),
                             'expectancy': bt.get('expectancy_R', ''),
                             'reasons': '; '.join(reasons)})
            except Exception as e:
                print(sym, tf, e)

    if rows:
        import pathlib
        pathlib.Path('logs').mkdir(exist_ok=True)
        log = pd.DataFrame(rows)
        try:
            old = pd.read_csv('logs/signals.csv')
            log = pd.concat([old, log]).tail(5000)
        except FileNotFoundError:
            pass
        log.to_csv('logs/signals.csv', index=False)

    # alerts with photo + confidence gate
    for r in rows:
        if (r['verdict'] != 'WAIT'
                and r['confidence'] >= cfg['min_confidence_to_alert']
                and r['tf'] in cfg['notify_timeframes']):
            msg = (f"*📊 {r['symbol']} {r['tf']}*\n"
                   f"Opinion: *{r['verdict']}* | Score {r['score']} | 🔥 Confidence *{r['confidence']}/100*\n")
            if r['win_rate'] != '':
                msg += f"Backtest: {r['win_rate']}% WR, expectancy {r['expectancy']}R\n"
            msg += f"Signals: {r['reasons']}\n\n"
            msg += gemini_opinion(r['symbol'], r['tf'], r['score'],
                                  r['reasons'].split('; '), {}, r['confidence'])
            try:
                # re-fetch df just for the chart (fresh data)
                dfc = fetch_binance(r['symbol'].replace('/', ''), r['tf']) if 'USDT' in r['symbol'] \
                      else fetch_twelvedata(r['symbol'], r['tf'], td_key)
                buf = make_chart(dfc, r['symbol'], r['tf'], r['verdict'])
                send_telegram_photo(buf, msg)
            except Exception:
                send_telegram(msg)

if __name__ == '__main__':
    run()
