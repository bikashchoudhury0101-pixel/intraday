import streamlit as st
from streamlit_autorefresh import st_autorefresh
from SmartApi import SmartConnect
import pyotp
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
import config   # your credentials file

st.set_page_config(page_title="Intraday EMA VWAP Pivot Scanner", layout="wide")
st.title("Intraday Scanner – EMA 9/21 + VWAP + Fibonacci Pivot")

# Auto refresh every 90 seconds
st_autorefresh(interval=90 * 1000, key="scanner_refresh")

# ========== LOGIN ==========
@st.cache_resource(show_spinner="Logging into Angel One...")
def get_smartapi():
    obj = SmartConnect(api_key=config.API_KEY)
    totp = pyotp.TOTP(config.TOTP_SECRET).now()
    data = obj.generateSession(config.CLIENT_CODE, config.MPIN, totp)
    if data['status'] == False:
        st.error(f"Login failed: {data}")
        st.stop()
    return obj

smart = get_smartapi()

# ========== LOAD INSTRUMENT MASTER ==========
@st.cache_data(ttl=3600*6)
def load_instrument_master():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    data = requests.get(url, timeout=60).json()
    df = pd.DataFrame(data)
    # Only NSE Equity
    df = df[(df['exch_seg'] == 'NSE') & (df['symbol'].str.endswith('-EQ'))]
    df['symbol_clean'] = df['symbol'].str.replace('-EQ', '')
    return df.set_index('symbol_clean')['token'].to_dict()

token_map = load_instrument_master()

# ========== STOCK LIST (you can edit this) ==========
# Start with liquid stocks. Later you can add more.
STOCK_LIST = [
    # ===== Nifty 100 (Major) =====
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN", "BHARTIARTL", "ITC", "LT", "KOTAKBANK",
    "AXISBANK", "BAJFINANCE", "HINDUNILVR", "ASIANPAINT", "MARUTI", "SUNPHARMA", "TITAN", "WIPRO", "ULTRACEMCO", "NESTLEIND",
    "POWERGRID", "NTPC", "ONGC", "TATAMOTORS", "ADANIENT", "ADANIPORTS", "JSWSTEEL", "TATASTEEL", "HCLTECH", "TECHM",
    "BAJAJFINSV", "INDUSINDBK", "CIPLA", "DRREDDY", "DIVISLAB", "EICHERMOT", "HEROMOTOCO", "BAJAJ-AUTO", "GRASIM", "COALINDIA",
    "BPCL", "IOC", "HDFCLIFE", "SBILIFE", "APOLLOHOSP", "BRITANNIA", "HINDALCO", "TATACONSUM", "M&M", "PIDILITIND",
    "SIEMENS", "DLF", "GODREJCP", "HAVELLS", "DABUR", "AMBUJACEM", "SHREECEM", "ICICIPRULI", "SBICARD", "COLPAL",
    "BERGEPAINT", "MARICO", "BANKBARODA", "PNB", "CANBK", "UNIONBANK", "INDIGO", "ZOMATO", "PAYTM", "NYKAA",
    "IRCTC", "HAL", "BEL", "BHEL", "GAIL", "VEDL", "SAIL", "NMDC", "HINDPETRO", "PETRONET",

    # ===== Midcap / Popular Mid & Large =====
    "PERSISTENT", "COFORGE", "LUPIN", "AUROPHARMA", "BIOCON", "GLENMARK", "ALKEM", "TORNTPHARM", "LAURUSLABS", "SYNGENE",
    "DIXON", "POLYCAB", "ASTRAL", "CUMMINSIND", "ABB", "SIEMENS", "BHEL", "ASHOKLEY", "TVSMOTOR", "BALKRISIND",
    "MRF", "APOLLOTYRE", "MOTHERSON", "BHARATFORG", "EXIDEIND", "AMARAJABAT", "FEDERALBNK", "IDFCFIRSTB", "AUBANK", "RBLBANK",
    "BANDHANBNK", "YESBANK", "INDHOTEL", "IHCL", "LEMONTREE", "JUBLFOOD", "DEVYANI", "WESTLIFE", "TRENT", "PAGEIND",
    "ABFRL", "RAYMOND", "VMART", "SHOPERSTOP", "CROMPTON", "VOLTAS", "BLUESTARCO", "WHIRLPOOL", "ORIENTELEC", "SYMPHONY",
    "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "BRIGADE", "SOBHA", "PHOENIXLTD", "LODHA", "MACROTECH", "DLF", "GODREJIND",
    "PFC", "RECLTD", "IRFC", "HUDCO", "IREDA", "SJVN", "NHPC", "TATAPOWER", "ADANIGREEN", "ADANIPOWER",
    "JSWENERGY", "NTPC", "POWERGRID", "TORNTPOWER", "CESC", "NLCINDIA", "COALINDIA", "GMDC", "MOIL", "KIOCL",

    # ===== Smallcap / Additional Liquid Names =====
    "ANGELONE", "MOTILALOFS", "IIFL", "CDSL", "BSE", "MCX", "CAMS", "KFINTECH", "AFFLE", "ROUTE",
    "TANLA", "INTELLECT", "NEWGEN", "LATENTVIEW", "HAPPSTMNDS", "SONATSOFTW", "MASTEK", "ZENSARTECH", "CYIENT", "LTTS",
    "KPITTECH", "BIRLASOFT", "COFORGE", "PERSISTENT", "MPHASIS", "OFSS", "TATAELXSI", "L&TFH", "CHOLAFIN", "BAJAJHLDNG",
    "MANAPPURAM", "MUTHOOTFIN", "POONAWALLA", "IIFL", "FIVESTAR", "CREDITACC", "AAVAS", "HOMEFIRST", "APTUS", "CANFINHOME",
    "PNBHOUSING", "LICHSGFIN", "REPCOHOME", "GICRE", "NIACL", "ICICIGI", "STARHEALTH", "HDFCAMC", "NAM-INDIA", "UTIAMC",
    "ABSLAMC", "NIPPON", "KAJARIACER", "CERA", "HSIL", "SOMANY", "ORIENTBELL", "ASIANPAINT", "BERGEPAINT", "AKZOINDIA",
    "GNFC", "DEEPAKNTR", "CLEAN", "FINEORG", "ALKYLAMINE", "NAVINFLUOR", "SRF", "PIDILITIND", "AARTIIND", "ATUL",
    "SUDARSCHEM", "VINATIORGA", "ROSSARI", "ANURAS", "FLUOROCHEM", "PCBL", "CARBORUNIV", "GRINDWELL", "TIMKEN", "SKFINDIA",
    "SCHAEFFLER", "ENDURANCE", "SUPRAJIT", "MINDAIND", "SONACOMS", "VARROC", "FIEM", "LUMAXTECH", "JAMNAAUTO", "WHEELS",
    "APOLLOTYRE", "CEATLTD", "JKTYRE", "BALKRISIND", "MRF", "TVSSRICHAK", "FAGBEARING", "NBC", "TIMKEN", "SCHAEFFLER"
]
# ========== HELPER FUNCTIONS ==========
def get_5min_candles(token, days=3):
    try:
        to_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d 09:15")
        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIVE_MINUTE",
            "fromdate": from_date,
            "todate": to_date
        }
        data = smart.getCandleData(params)
        if data['status'] and data['data']:
            df = pd.DataFrame(data['data'], columns=['datetime','open','high','low','close','volume'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.astype({'open':float, 'high':float, 'low':float, 'close':float, 'volume':float})
            return df
    except Exception as e:
        pass
    return None

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_vwap(df):
    # Session VWAP (from market open)
    df = df.copy()
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['tp_vol'] = df['tp'] * df['volume']
    df['cum_tp_vol'] = df['tp_vol'].cumsum()
    df['cum_vol'] = df['volume'].cumsum()
    df['vwap'] = df['cum_tp_vol'] / df['cum_vol']
    return df['vwap'].iloc[-1]

def fibonacci_pivots(prev_high, prev_low, prev_close):
    pivot = (prev_high + prev_low + prev_close) / 3
    r1 = pivot + 0.382 * (prev_high - prev_low)
    s1 = pivot - 0.382 * (prev_high - prev_low)
    return pivot, r1, s1

# ========== MAIN SCAN ==========
long_list = []
short_list = []
progress = st.progress(0)
status = st.empty()

total = len(STOCK_LIST)

for i, symbol in enumerate(STOCK_LIST):
    status.text(f"Scanning {symbol} ({i+1}/{total})...")
    progress.progress((i + 1) / total)

    token = token_map.get(symbol)
    if not token:
        continue

    df = get_5min_candles(str(token))
    if df is None or len(df) < 30:
        time.sleep(0.4)
        continue

    # Current values
    ltp = df['close'].iloc[-1]
    ema9 = calculate_ema(df['close'], 9).iloc[-1]
    ema21 = calculate_ema(df['close'], 21).iloc[-1]
    vwap = calculate_vwap(df)

    # Volume ratio (last bar vs average of previous 20)
    avg_vol = df['volume'].iloc[-21:-1].mean()
    curr_vol = df['volume'].iloc[-1]
    vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1

    # Previous day approximate (last full day candles)
    df['date'] = df['datetime'].dt.date
    unique_dates = df['date'].unique()
    if len(unique_dates) >= 2:
        prev_day = df[df['date'] == unique_dates[-2]]
        prev_high = prev_day['high'].max()
        prev_low = prev_day['low'].min()
        prev_close = prev_day['close'].iloc[-1]
    else:
        prev_high = df['high'].max()
        prev_low = df['low'].min()
        prev_close = df['close'].iloc[-1]

    pivot, r1, s1 = fibonacci_pivots(prev_high, prev_low, prev_close)

    # Distance to R1 / S1 in %
    dist_r1 = abs(ltp - r1) / ltp * 100
    dist_s1 = abs(ltp - s1) / ltp * 100

    # Change %
    open_price = df['open'].iloc[0] if len(df) > 0 else ltp
    change_pct = ((ltp - open_price) / open_price) * 100

    # ========== LONG CONDITIONS ==========
    if (ltp > ema9 and ltp > ema21 and ltp > vwap and 
        vol_ratio > 1.4 and dist_r1 < 0.35):
        long_list.append({
            "Symbol": symbol,
            "LTP": round(ltp, 2),
            "Change %": round(change_pct, 2),
            "Vol Ratio": round(vol_ratio, 2),
            "Dist to R1 %": round(dist_r1, 2),
            "EMA9": round(ema9, 2),
            "EMA21": round(ema21, 2),
            "VWAP": round(vwap, 2),
            "R1": round(r1, 2)
        })

    # ========== SHORT CONDITIONS ==========
    if (ltp < ema9 and ltp < ema21 and ltp < vwap and 
        vol_ratio < 0.7 and dist_s1 < 0.35):
        short_list.append({
            "Symbol": symbol,
            "LTP": round(ltp, 2),
            "Change %": round(change_pct, 2),
            "Vol Ratio": round(vol_ratio, 2),
            "Dist to S1 %": round(dist_s1, 2),
            "EMA9": round(ema9, 2),
            "EMA21": round(ema21, 2),
            "VWAP": round(vwap, 2),
            "S1": round(s1, 2)
        })

    time.sleep(0.45)   # respect rate limits

progress.empty()
status.empty()

# ========== DISPLAY ==========
col1, col2 = st.columns(2)

with col1:
    st.subheader(f"🟢 LONG Candidates ({len(long_list)})")
    if long_list:
        st.dataframe(pd.DataFrame(long_list), use_container_width=True, hide_index=True)
    else:
        st.info("No long setups right now")

with col2:
    st.subheader(f"🔴 SHORT Candidates ({len(short_list)})")
    if short_list:
        st.dataframe(pd.DataFrame(short_list), use_container_width=True, hide_index=True)
    else:
        st.info("No short setups right now")

st.caption(f"Last scanned: {datetime.now().strftime('%H:%M:%S')} | Auto-refresh every 90 seconds | Stocks scanned: {total}")