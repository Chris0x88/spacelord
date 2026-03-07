import io
from datetime import datetime, timedelta
import pandas as pd
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

def download_binance_klines(start_time: int, end_time: int) -> pd.DataFrame:
    import requests
    url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&startTime={start_time}&endTime={end_time}&limit=1000"
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

def generate_powerlaw_png() -> bytes:
    """
    Fetch history from Binance, generate a high-definition static PNG of the Power Law Heartbeat Model.
    Returns bytes of the PNG image.
    """
    # Fetch 4 years of history (start of cycle 4 + 1 year)
    end_time = int(datetime.utcnow().timestamp() * 1000)
    start_time = int(HALVINGS[-1].timestamp() * 1000) - int(365 * 24 * 60 * 60 * 1000) # go back a year before last halving
    
    try:
        df = download_binance_klines(start_time, end_time)
        if df.empty:
            raise ValueError("No data returned from Binance")
    except Exception as e:
        logger.error(f"[Charting] Failed to fetch binance history: {e}")
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
    
    # Smooth moving average
    df['sma100'] = df['price'].rolling(window=100).mean()

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
    s5, e5 = cycle_bounds(5)
    t5 = (e5 - s5).total_seconds()
    z5_start = s5 + timedelta(seconds=t5*0.26)
    z5_end = s5 + timedelta(seconds=t5*0.39)
    ax.axvspan(mdates.date2num(z5_start), mdates.date2num(z5_end), 
               color='#fbbf24', alpha=0.1, lw=0)
    
    # Position the Peak Zone text near the top
    ax.text(mdates.date2num(z5_start + (z5_end - z5_start)/2), 
            0.9, 'Peak Zone', transform=ax.get_xaxis_transform(),
            color='#fbbf24', alpha=0.6, ha='center', va='top', fontsize=8, fontweight='bold', rotation=90)

    # 5. Plot lines
    # Ceiling
    ax.plot(all_dates, pd.concat([df['ceiling'], future_df['ceiling']]), 
            color='#ef4444', linewidth=1.5, label='Ceiling')
    
    # Floor
    ax.plot(all_dates, pd.concat([df['floor'], future_df['floor']]), 
            color='#10b981', linewidth=1.5, label='Floor')
            
    # Model Price
    ax.plot(all_dates, pd.concat([df['model_price'], future_df['model_price']]), 
            color='#a855f7', linewidth=2.0, linestyle='--', alpha=0.8, label='Fair Value')

    # BTC Price
    ax.plot(df['date'], df['price'], color='#06b6d4', linewidth=2.0, alpha=0.9, label='BTC Price')

    # SMA 100
    ax.plot(df['date'], df['sma100'], color='#22d3ee', linewidth=1.0, linestyle=':', alpha=0.8, label='SMA 100')

    # "NOW" Line
    ax.axvline(x=mdates.date2num(last_date), color='#f97316', linestyle='--', linewidth=1.0, alpha=0.6)
    ax.text(mdates.date2num(last_date) - 15, 0.05, 'NOW', transform=ax.get_xaxis_transform(),
            color='#f97316', alpha=0.8, ha='right', va='bottom', fontsize=8, fontweight='bold')

    # Formatting axes
    ax.set_yscale('linear')
    
    # Set limits based on the recent halving minus a bit to focus the chart
    recent_start = pd.Timestamp("2023-01-01")  # Focus on the relevant recent period
    ax.set_xlim(recent_start, future_dates[-1])
    
    # Set y limit smartly based on ceiling in the visible window
    visible_df = future_df[future_df['date'] <= future_dates[-1]]
    max_visible_ceiling = visible_df['ceiling'].max()
    ax.set_ylim(bottom=0, top=max_visible_ceiling * 1.1)

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
