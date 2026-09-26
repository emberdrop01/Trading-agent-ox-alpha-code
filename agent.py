import os, json, requests, pandas as pd
from datetime import datetime, timezone
import google.generativeai as genai
from strategy import analyze, trend, golden_cross
from backtest import backtest

TF_MAP = {'15min':'15min','30min':'30min','1h':'1h','4h':'4h','1day':'1day'}

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

def gemini_opinion(symbol, tf, score, reasons, bt):
    try:
        genai.configure(api_key=os.environ['GEMINI_API_KEY'])
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = (f"You are a strict technical analyst. Symbol {symbol} timeframe {tf}. "
                  f"Confluence score {score}. Signals: {reasons}. "
                  f"Backtest on 500+ candles: {json.dumps(bt)}. "
                  f"Give a 3-line opinion: bias (BUY/SELL/WAIT), key levels to watch, risk note. Opinion only, not financial advice.")
        return model.generate_content(prompt).text
    except Exception as e:
        return f"(Gemini unavailable: {e})"

SYMBOLS = json.loads(os.environ.get('SYMBOLS', '["BTC/USDT","ETH/USDT"]'))

def run():
    td_key = os.environ.get('TWELVEDATA_KEY', '')
    rows = []
    for sym in SYMBOLS:
        for tf in ['15min','30min','1h','4h','1day']:
            try:
                df = fetch_twelvedata(sym, tf, td_key) if td_key else fetch_binance(sym.replace('/',''), tf)
                if len(df) < 250: continue
                score, reasons, fvg = analyze(df)
                bt = backtest(df) if abs(score) >= 3 else {}
                verdict = "BUY" if score >= 3 else "SELL" if score <= -3 else "WAIT"
                ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
                rows.append({'time': ts, 'symbol': sym, 'tf': tf, 'verdict': verdict,
                             'score': score, 'win_rate': bt.get('win_rate_%',''),
                             'expectancy': bt.get('expectancy_R',''), 'reasons': '; '.join(reasons)})
                print(sym, tf, e)
                # save log
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

# telegram alert: only report actionable signals on 30min+ (per your 30-min notify)
for r in rows:
    if r['verdict'] != 'WAIT' and r['tf'] in ('30min','1h','4h','1day'):
        msg = (f"*📊 {r['symbol']} {r['tf']}*\n"
               f"Opinion: *{r['verdict']}* (score {r['score']})\n")
        if r['win_rate'] != '':
            msg += (f"Backtest: {r['win_rate']}% win rate, expectancy {r['expectancy']}R\n")
        msg += f"Signals: {r['reasons']}\n"
        msg += gemini_opinion(r['symbol'], r['tf'], r['score'], r['reasons'].split('; '), {})
        send_telegram(msg)
if name == 'main':
run()


