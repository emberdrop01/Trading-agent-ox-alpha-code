import asyncio, json
import pandas as pd

APP_ID = "1089"          # public Deriv app id
WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"

# our symbols -> Deriv symbol codes
DERIV_SYMBOLS = {
    "V75":        "R_100",
    "V75(1s)":    "1HZ100V",
    "V50":        "R_50",
    "V25":        "R_25",
    "V10":        "R_10",
    "BOOM500":    "BOOM500",
    "BOOM1000":   "BOOM1000",
    "CRASH500":   "CRASH500",
    "CRASH1000":  "CRASH1000",
    "STEP":       "stpRNG",
    "JUMP10":     "JD10",
    "JUMP25":     "JD25",
    "JUMP50":     "JD50",
    "JUMP75":     "JD75",
    "JUMP100":    "JD100",
}

DERIV_TFS = {  # our timeframe -> deriv granularity (seconds)
    "1min": 60, "5min": 300, "15min": 900, "30min": 1800, "1h": 3600, "4h": 14400
}

async def _fetch(symbol_code, granularity, count=600):
    import websockets
    async with websockets.connect(WS_URL, ping_interval=20) as ws:
        await ws.send(json.dumps({
            "ticks_history": symbol_code,
            "adjust_start_time": 1, "count": count, "end": "latest",
            "style": "candles", "granularity": granularity
        }))
        while True:
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            if resp.get("msg_type") == "candles":
                c = resp["candles"]
                df = pd.DataFrame(c).astype(float)
                df.columns = ['datetime','open','high','low','close']
                df['volume'] = 0
                return df
            if "error" in resp:
                raise RuntimeError(resp["error"]["message"])

def fetch_deriv(our_symbol, our_tf, count=600):
    """Blocking wrapper — call this from agent.py."""
    code = DERIV_SYMBOLS[our_symbol]
    gran = DERIV_TFS[our_tf]
    return asyncio.run(_fetch(code, gran, count))
