import io
from datetime import datetime, timedelta
import pandas as pd
import requests
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

from src.logger import logger
from src.plugins.power_law.heartbeat_model import (
    floor_price, ceiling_price, model_price, 
    HALVINGS, get_halving_date, GENESIS
)

def cycle_bounds(c: int) -> tuple[datetime, datetime]:
    if c == 1:
        return (GENESIS, get_halving_date(1))
    return (get_halving_date(c - 1), get_halving_date(c))

def download_binance_klines(start_time_ms: int, end_time_ms: int) -> pd.DataFrame:
    """Fetch 1d candles from Binance. Uses 1d for high-fidelity trend data."""
    url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&startTime={start_time_ms}&limit=1000"
    r = requests.get(url, timeout=5)
    data = r.json()
    if not isinstance(data, list) or len(data) == 0:
        return pd.DataFrame()
        
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
    ])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['price'] = df['close'].astype(float)
    return df[['date', 'price']].copy()

def get_incremental_btc_history() -> pd.DataFrame:
    """
    Maintains a local JSON cache of BTC price history.
    Fetches only missing candles from Binance to reach 'Today'.
    """
    cache_path = Path("data/btc_history_1d.json")
    df_cache = pd.DataFrame(columns=['date', 'price'])
    
    # 1. Load existing cache
    if cache_path.exists():
        try:
            df_cache = pd.read_json(cache_path)
            df_cache['date'] = pd.to_datetime(df_cache['date'])
        except Exception as e:
            logger.warning(f"Failed to load BTC history cache: {e}")

    # 2. Determine where to start fetching
    # Start from Binance inception if cache empty, else last cached date + 1 day
    if not df_cache.empty:
        last_date = df_cache['date'].max()
        start_time_ms = int((last_date + timedelta(days=1)).timestamp() * 1000)
    else:
        # Binance BTCUSDT inception is roughly Aug 17, 2017
        start_time_ms = int(pd.Timestamp("2017-08-17").timestamp() * 1000)

    now_ms = int(datetime.utcnow().timestamp() * 1000)
    
    # 3. Paginated fetch loop
    new_data = []
    current_start = start_time_ms
    
    while current_start < now_ms:
        logger.info(f"   📡 Fetching BTC history from {pd.to_datetime(current_start, unit='ms')}...")
        batch_df = download_binance_klines(current_start, now_ms)
        if batch_df.empty:
            break
            
        new_data.append(batch_df)
        last_ms = int(batch_df['date'].iloc[-1].timestamp() * 1000)
        
        # If we got less than 1000, we're done; otherwise move start to last candle + 1 day
        if len(batch_df) < 1000:
            break
        current_start = last_ms + (24 * 60 * 60 * 1000)

    # 4. Merge and save
    if new_data:
        df_new = pd.concat(new_data).drop_duplicates('date')
        df_combined = pd.concat([df_cache, df_new]).drop_duplicates('date').sort_values('date').reset_index(drop=True)
        
        # Ensure data directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df_combined.to_json(cache_path, date_format='iso', indent=2)
        return df_combined
        
    return df_cache

def generate_powerlaw_png() -> bytes:
    """
    Fetch history from cache/Binance, generate a high-definition static PNG.
    """
    df = get_incremental_btc_history()
    if df.empty:
        logger.error("[Charting] No BTC history available.")
        return b''
    
    # 1. Setup dark theme aesthetics
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    fig.patch.set_facecolor('#0f172a') # Tailwind slate-900
    ax.set_facecolor('#0f172a')
    
    # Grid and spines
    ax.grid(True, color='#334155', linestyle='--', linewidth=0.5, alpha=0.5)
    for spine in ax.spines.values():
        spine.set_color('#334155')
        
    df = df.copy()
    if 'date' not in df.columns or 'price' not in df.columns:
        raise ValueError("DataFrame must contain 'date' and 'price' columns")
        
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # 2. Compute model metrics natively
    df['floor'] = df['date'].apply(floor_price)
    df['ceiling'] = df['date'].apply(ceiling_price)
    df['model_price'] = df['date'].apply(model_price)
    
    # Smooth moving average (200 days)
    df['sma200'] = df['price'].rolling(window=200).mean()

    # 3. Add future projections (only 1 year out to avoid empty space)
    last_date = df['date'].iloc[-1]
    future_dates = [last_date + timedelta(days=i) for i in range(1, 365, 7)] # 1 year out
    future_df = pd.DataFrame({'date': future_dates})
    future_df['floor'] = future_df['date'].apply(floor_price)
    future_df['ceiling'] = future_df['date'].apply(ceiling_price)
    future_df['model_price'] = future_df['date'].apply(model_price)
    
    # Combine for unified plotting paths
    all_dates = pd.concat([df['date'], future_df['date']])
    
    # 4. Plot Peak Zones (Golden Windows)
    # Cycle 4 peak (2021)
    s4, e4 = cycle_bounds(4)
    t4 = (e4 - s4).total_seconds()
    z4_start = s4 + timedelta(seconds=t4*0.26)
    z4_end = s4 + timedelta(seconds=t4*0.39)
    ax.axvspan(mdates.date2num(z4_start), mdates.date2num(z4_end), 
               color='#fbbf24', alpha=0.1, lw=0)
    ax.text(mdates.date2num(z4_start + (z4_end - z4_start)/2), 
            0.85, 'CRYPTO PEAK WINDOW', transform=ax.get_xaxis_transform(),
            color='#fbbf24', alpha=0.8, ha='center', va='top', fontsize=9, fontweight='bold', rotation=0)

    # Cycle 5 peak (current cycle)
    s5, e5 = cycle_bounds(5)
    t5 = (e5 - s5).total_seconds()
    z5_start = s5 + timedelta(seconds=t5*0.26)
    z5_end = s5 + timedelta(seconds=t5*0.39)
    ax.axvspan(mdates.date2num(z5_start), mdates.date2num(z5_end), 
               color='#fbbf24', alpha=0.1, lw=0)
    
    # Position the Peak Zone text near the top
    ax.text(mdates.date2num(z5_start + (z5_end - z5_start)/2), 
            0.85, 'CRYPTO PEAK WINDOW', transform=ax.get_xaxis_transform(),
            color='#fbbf24', alpha=0.8, ha='center', va='top', fontsize=9, fontweight='bold', rotation=0)

    # 5. Plot Model Corridor (Fill)
    ax.fill_between(all_dates, 
                    pd.concat([df['floor'], future_df['floor']]), 
                    pd.concat([df['ceiling'], future_df['ceiling']]), 
                    color='#334155', alpha=0.2, label='Model Corridor')
    
    # Floor (Dashed)
    ax.plot(all_dates, pd.concat([df['floor'], future_df['floor']]), 
            color='#10b981', linewidth=1.0, linestyle=':', alpha=0.5)
            
    # Model Price (Fair Value)
    ax.plot(all_dates, pd.concat([df['model_price'], future_df['model_price']]), 
            color='#a855f7', linewidth=2.0, linestyle='--', alpha=0.8, label='MODEL FAIR VALUE')

    # BTC Market Price (Prominent)
    ax.plot(df['date'], df['price'], color='#06b6d4', linewidth=2.5, alpha=1.0, label='BTC MARKET PRICE')

    # SMA 200 (Daily)
    df_sma = df.dropna(subset=['sma200'])
    ax.plot(df_sma['date'], df_sma['sma200'], color='#22d3ee', linewidth=1.0, linestyle='-', alpha=0.4, label='200d Avg')

    # "NOW" Line
    ax.axvline(x=mdates.date2num(last_date), color='#f97316', linestyle='-', linewidth=1.5, alpha=0.8)
    
    # 6. Formatting axes
    ax.set_yscale('linear')
    
    # Set limits: focus to include the 2021 market top
    recent_start = pd.Timestamp("2021-01-01") 
    ax.set_xlim(recent_start, last_date + timedelta(days=365)) # 12 months projection
    
    # Dynamic Y limits
    visible_hist = df[df['date'] >= recent_start]
    max_price_in_view = max(visible_hist['price'].max(), df['model_price'].max())
    
    ax.set_ylim(bottom=min(visible_hist['price'].min(), 40000) * 0.9, 
                top=max_price_in_view * 1.15)

    # Add numeric labels at the 'NOW' line for total clarity
    current_btc = df['price'].iloc[-1]
    current_fair = df['model_price'].iloc[-1]
    
    ax.annotate(f' MARKET: ${current_btc/1000:.1f}k', xy=(last_date, current_btc),
                xytext=(10, 0), textcoords='offset points', color='#06b6d4', 
                fontweight='bold', fontsize=10, va='center')

    ax.annotate(f' FAIR VAL: ${current_fair/1000:.1f}k', xy=(last_date, current_fair),
                xytext=(10, 0), textcoords='offset points', color='#a855f7', 
                fontweight='bold', fontsize=10, va='center')

    # Ticks
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    import matplotlib.ticker as ticker
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, pos: f'${int(y/1000)}k' if y >= 1000 else f'${int(y)}'))
    
    ax.tick_params(axis='both', colors='#94a3b8', labelsize=9)
    plt.xticks(rotation=45)

    # Legends & Titles
    ax.legend(loc='upper left', frameon=False, labelcolor='#cbd5e1', fontsize=9, ncol=2)
    ax.set_title("Bitcoin Power Law: Heartbeat Transform", color='white', pad=20, fontsize=14, fontweight='bold', loc='left')

    out = io.BytesIO()
    plt.tight_layout()
    # Adding a title timestamp
    plt.title(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", loc='right', color='#64748b', fontsize=8)
    plt.savefig(out, format='png', facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close(fig)
    out.seek(0)
    return out.read()
