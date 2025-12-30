import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from kafka import KafkaConsumer
import json
import os
import mlflow
from mlflow.tracking import MlflowClient
import datetime
import numpy as np
from sklearn.preprocessing import StandardScaler
import pickle

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Crypto Intelligence Platform",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
KAFKA_BOOTSTRAP = "kafka:29092"
HDFS_FEATURES_PATH = "/data/crypto/features"
MLFLOW_URI = "http://mlflow:5000"

# ==========================================
# MODERN PROFESSIONAL STYLING - BRIGHT & CLEAN
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Poppins:wght@400;500;600;700;800&display=swap');
    
    /* Base Theme - Clean & Bright */
    .main {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f0f9ff 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Headers */
    h1 {
        font-family: 'Poppins', sans-serif !important;
        font-weight: 800 !important;
        color: #0369a1 !important;
        font-size: 2.8rem !important;
        margin-bottom: 0.5rem !important;
        letter-spacing: -0.5px;
    }
    
    h2, h3 {
        font-family: 'Poppins', sans-serif !important;
        font-weight: 700 !important;
        color: #0c4a6e !important;
        letter-spacing: -0.3px;
    }
    
    /* Metric Cards - Bright & Professional */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 2px solid #38bdf8;
        padding: 22px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(14, 165, 233, 0.15);
        transition: all 0.3s ease;
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(14, 165, 233, 0.25);
        border-color: #0ea5e9;
    }
    
    div[data-testid="metric-container"] label {
        color: #0369a1 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #0c4a6e !important;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        font-family: 'Poppins', sans-serif !important;
    }
    
    div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
    }
    
    /* Tabs - Clean Modern Design */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: #ffffff;
        padding: 12px;
        border-radius: 16px;
        box-shadow: 0 2px 12px rgba(3, 105, 161, 0.08);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 56px;
        background: #f1f5f9;
        border-radius: 12px;
        color: #475569;
        font-weight: 600;
        font-size: 0.95rem;
        padding: 0 28px;
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: #e0f2fe;
        color: #0369a1;
        border-color: #bae6fd;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
        color: white !important;
        border-color: #0ea5e9 !important;
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
    }
    
    /* Buttons - Vibrant & Modern */
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 14px 32px;
        font-weight: 700;
        font-size: 0.95rem;
        letter-spacing: 0.3px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.3);
        font-family: 'Poppins', sans-serif;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(14, 165, 233, 0.4);
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
    }
    
    /* Sidebar - Clean Professional */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border-right: 3px solid #bae6fd;
    }
    
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #0369a1 !important;
    }
    
    /* Data Frames - Clean & Readable */
    .dataframe {
        background: white !important;
        border: 2px solid #e0f2fe !important;
        border-radius: 12px !important;
        font-size: 0.9rem !important;
    }
    
    .dataframe th {
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        padding: 12px !important;
    }
    
    .dataframe td {
        padding: 10px !important;
        color: #1e293b !important;
    }
    
    /* Info Boxes - Bright & Clear */
    .stAlert {
        background: white !important;
        border: 2px solid #38bdf8 !important;
        border-radius: 12px !important;
        color: #0c4a6e !important;
        box-shadow: 0 2px 8px rgba(14, 165, 233, 0.1) !important;
    }
    
    .stSuccess {
        background: #f0fdf4 !important;
        border: 2px solid #4ade80 !important;
        color: #15803d !important;
    }
    
    .stWarning {
        background: #fffbeb !important;
        border: 2px solid #fbbf24 !important;
        color: #92400e !important;
    }
    
    .stError {
        background: #fef2f2 !important;
        border: 2px solid #f87171 !important;
        color: #991b1b !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background: white !important;
        border: 2px solid #bae6fd !important;
        border-radius: 10px !important;
        color: #0369a1 !important;
        font-weight: 600 !important;
        padding: 12px !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: #f0f9ff !important;
        border-color: #38bdf8 !important;
    }
    
    /* Progress Bars */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #0ea5e9 0%, #06b6d4 100%);
    }
    
    /* Selectbox, Input, etc */
    .stSelectbox, .stMultiSelect, .stNumberInput, .stTextInput {
        background: white !important;
    }
    
    [data-baseweb="select"] > div {
        background: white !important;
        border: 2px solid #bae6fd !important;
        border-radius: 10px !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
        border-radius: 6px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);
        border-radius: 6px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
    }
    
    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.3px;
    }
    
    .status-success {
        background: #dcfce7;
        color: #15803d;
        border: 2px solid #86efac;
    }
    
    .status-warning {
        background: #fef3c7;
        color: #92400e;
        border: 2px solid #fcd34d;
    }
    
    .status-error {
        background: #fee2e2;
        color: #991b1b;
        border: 2px solid #fca5a5;
    }
    
    /* Cards */
    .info-card {
        background: white;
        border: 2px solid #bae6fd;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 2px 12px rgba(14, 165, 233, 0.1);
        transition: all 0.3s ease;
    }
    
    .info-card:hover {
        box-shadow: 0 4px 20px rgba(14, 165, 233, 0.2);
        transform: translateY(-2px);
    }
    
    /* Code blocks */
    code {
        background: #e0f2fe !important;
        color: #0369a1 !important;
        padding: 3px 8px !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        border: 1px solid #bae6fd !important;
    }
    
    /* Dividers */
    hr {
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, transparent 0%, #bae6fd 50%, transparent 100%) !important;
        margin: 2rem 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# HEADER SECTION
# ==========================================
st.markdown("""
<div style='text-align: center; padding: 2rem 0 1.5rem 0; background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%); 
            border-radius: 20px; margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(14, 165, 233, 0.15);'>
    <h1 style='margin-bottom: 0.5rem; font-size: 3.2rem;'>💎 CRYPTO INTELLIGENCE PLATFORM</h1>
    <p style='font-size: 1.15rem; color: #0369a1; font-weight: 600; letter-spacing: 0.5px; margin: 0;'>
        Real-Time Big Data Analytics & Machine Learning
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style='background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%); padding: 1.2rem; 
            border-radius: 14px; margin-bottom: 2rem; border: 2px solid #38bdf8;'>
    <p style='margin: 0; text-align: center; color: #0c4a6e; font-size: 1rem; font-weight: 600;'>
        <strong>Data Pipeline:</strong> 
        <span style='color: #0ea5e9; font-weight: 700;'>Kafka</span> → 
        <span style='color: #0ea5e9; font-weight: 700;'>Spark Streaming</span> → 
        <span style='color: #0ea5e9; font-weight: 700;'>HDFS</span> → 
        <span style='color: #0ea5e9; font-weight: 700;'>MLflow</span> → 
        <span style='color: #0ea5e9; font-weight: 700;'>Real-Time Predictions</span>
    </p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# SIDEBAR - SYSTEM MONITOR
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center; margin-bottom: 1.5rem;'>🔧 System Monitor</h2>", unsafe_allow_html=True)
    
    def check_system_health():
        health = {
            "Kafka Broker": {"status": "Offline", "icon": "🔴", "color": "#ef4444"},
            "HDFS Storage": {"status": "No Data", "icon": "🔴", "color": "#ef4444"},
            "MLflow Tracking": {"status": "Disconnected", "icon": "🔴", "color": "#ef4444"},
            "Spark Processing": {"status": "Idle", "icon": "🔴", "color": "#ef4444"}
        }
        
        try:
            consumer = KafkaConsumer(bootstrap_servers=KAFKA_BOOTSTRAP, consumer_timeout_ms=1000)
            if consumer.bootstrap_connected():
                health["Kafka Broker"] = {"status": "Connected", "icon": "🟢", "color": "#10b981"}
            consumer.close()
        except:
            pass
        
        if os.path.exists(HDFS_FEATURES_PATH) and len(os.listdir(HDFS_FEATURES_PATH)) > 0:
            health["HDFS Storage"] = {"status": "Active", "icon": "🟢", "color": "#10b981"}
            health["Spark Processing"] = {"status": "Running", "icon": "🟢", "color": "#10b981"}
        
        try:
            mlflow.set_tracking_uri(MLFLOW_URI)
            client = MlflowClient()
            if client.search_experiments():
                health["MLflow Tracking"] = {"status": "Online", "icon": "🟢", "color": "#10b981"}
        except:
            pass
        
        return health
    
    health_status = check_system_health()
    
    for component, info in health_status.items():
        st.markdown(f"""
        <div style='background: white; padding: 14px; border-radius: 10px; 
                    border-left: 5px solid {info['color']}; margin-bottom: 12px;
                    box-shadow: 0 2px 8px rgba(14, 165, 233, 0.08);'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <strong style='color: #0c4a6e; font-size: 0.9rem;'>{component}</strong>
                <span style='font-size: 1.2rem;'>{info['icon']}</span>
            </div>
            <p style='margin: 4px 0 0 0; color: #64748b; font-size: 0.85rem;'>{info['status']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("<h3 style='margin-bottom: 1rem;'>📊 Project Info</h3>", unsafe_allow_html=True)
    
    with st.expander("🎯 Architecture", expanded=False):
        st.markdown("""
        **Data Pipeline:**
        - **Producer**: Real-time crypto data ingestion
        - **Kafka**: Distributed message streaming
        - **Spark**: Big data processing & features
        - **HDFS**: Distributed data storage
        - **MLflow**: Model tracking & versioning
        
        **Data Volume:** ~8GB+ crypto data
        """)
    
    with st.expander("🤖 ML Models", expanded=False):
        st.markdown("""
        **1. Trend Prediction**
        - Logistic Regression
        - Task: Up/Down classification
        
        **2. Anomaly Detection**
        - Random Forest
        - Task: Outlier detection
        """)
    
    st.markdown("---")
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); 
                padding: 14px; border-radius: 10px; border: 2px solid #93c5fd;'>
        <p style='margin: 0; color: #1e40af; font-size: 0.85rem; font-weight: 600;'>
            💡 <strong>Tip:</strong> Enable auto-refresh for live monitoring
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=False)

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def normalize_prices(df):
    """Normalize prices for comparison"""
    df_norm = df.copy()
    for symbol in df_norm['symbol'].unique():
        mask = df_norm['symbol'] == symbol
        first_price = df_norm.loc[mask, 'price'].iloc[0]
        if first_price > 0:
            df_norm.loc[mask, 'norm_price'] = ((df_norm.loc[mask, 'price'] - first_price) / first_price) * 100
        else:
            df_norm.loc[mask, 'norm_price'] = 0
    return df_norm

def create_modern_gauge(value, title, min_val=0, max_val=100, threshold=50):
    """Create a modern gauge chart"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'color': '#0369a1', 'size': 18, 'family': 'Poppins'}},
        delta={'reference': threshold, 'increasing': {'color': "#10b981"}, 'decreasing': {'color': "#ef4444"}},
        gauge={
            'axis': {'range': [min_val, max_val], 'tickcolor': "#0ea5e9", 'tickfont': {'size': 12}},
            'bar': {'color': "#0ea5e9", 'thickness': 0.8},
            'bgcolor': "white",
            'borderwidth': 3,
            'bordercolor': "#bae6fd",
            'steps': [
                {'range': [min_val, threshold], 'color': "#dbeafe"},
                {'range': [threshold, max_val], 'color': "#fee2e2"}
            ],
            'threshold': {
                'line': {'color': "#ef4444", 'width': 4},
                'thickness': 0.8,
                'value': threshold
            }
        }
    ))
    
    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor="white",
        font={'color': "#0c4a6e", 'family': "Inter"}
    )
    return fig

def create_plot_layout(title, height=400):
    """Modern plot styling"""
    return dict(
        title=dict(text=title, font=dict(size=20, color='#0c4a6e', family='Poppins', weight='bold')),
        height=height,
        paper_bgcolor='white',
        plot_bgcolor='#f8fafc',
        font=dict(color='#0c4a6e', family='Inter'),
        hovermode='x unified',
        xaxis=dict(
            gridcolor='#e2e8f0',
            showgrid=True,
            zeroline=False,
            linecolor='#cbd5e1'
        ),
        yaxis=dict(
            gridcolor='#e2e8f0',
            showgrid=True,
            zeroline=False,
            linecolor='#cbd5e1'
        ),
        margin=dict(l=50, r=50, t=60, b=50)
    )

# ==========================================
# MAIN TABS
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Live Market Dashboard",
    "🔥 Real-Time Stream",
    "⚠️ Anomaly Detection",
    "🤖 ML Performance",
    "🎯 Predictions"
])

# ==========================================
# TAB 1: MARKET DASHBOARD
# ==========================================
with tab1:
    st.markdown("<h2 style='margin-bottom: 1.5rem;'>📊 Comprehensive Market Dashboard</h2>", unsafe_allow_html=True)
    
    refresh_market = st.button("🔄 Refresh Market Data", key="refresh_tab1")
    
    if refresh_market or auto_refresh:
        with st.spinner("🔍 Fetching live market data..."):
            try:
                consumer = KafkaConsumer(
                    'crypto_raw',
                    bootstrap_servers=KAFKA_BOOTSTRAP,
                    auto_offset_reset='earliest',
                    enable_auto_commit=False,
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                    consumer_timeout_ms=2000
                )
                
                raw_data = []
                for message in consumer:
                    raw_data.append(message.value)
                consumer.close()
                
                if raw_data:
                    df_raw = pd.DataFrame(raw_data)
                    df_raw['timestamp'] = pd.to_datetime(df_raw['timestamp'])
                    df_raw = df_raw.sort_values('timestamp')
                    
                    # === KEY METRICS ===
                    st.markdown("### 💰 Global Market Metrics")
                    latest = df_raw.groupby('symbol').last().reset_index()
                    
                    m1, m2, m3, m4, m5 = st.columns(5)
                    
                    total_vol = latest['volume'].sum()
                    top_gainer = latest.loc[latest['price_change_24h'].idxmax()]
                    top_loser = latest.loc[latest['price_change_24h'].idxmin()]
                    avg_change = latest['price_change_24h'].mean()
                    active_coins = len(latest)
                    
                    m1.metric("💰 Total Volume", f"${total_vol:,.0f}", 
                             delta=f"{len(df_raw)} points")
                    m2.metric("🚀 Top Gainer", f"{top_gainer['symbol'].upper()}", 
                             delta=f"+{top_gainer['price_change_24h']:.2f}%")
                    m3.metric("📉 Top Loser", f"{top_loser['symbol'].upper()}", 
                             delta=f"{top_loser['price_change_24h']:.2f}%")
                    m4.metric("📊 Avg Change", f"{avg_change:.2f}%")
                    m5.metric("🪙 Active Coins", f"{active_coins}")
                    
                    st.markdown("---")
                    
                    # === MARKET PULSE ===
                    st.markdown("### 🌊 Market Pulse - Comparative Performance")
                    st.caption("All cryptocurrencies normalized to 0% at stream start")
                    
                    df_norm = normalize_prices(df_raw)
                    
                    # Distinctive color palette for each cryptocurrency
                    crypto_colors = {
                        'bitcoin': '#F7931A',      # Bitcoin Orange
                        'ethereum': '#627EEA',     # Ethereum Purple
                        'cardano': '#0033AD',      # Cardano Blue
                        'solana': '#14F195',       # Solana Green
                        'polkadot': '#E6007A',     # Polkadot Pink
                        'ripple': '#00AAE4',       # Ripple Blue
                        'dogecoin': '#C2A633',     # Dogecoin Gold
                        'avalanche': '#E84142',    # Avalanche Red
                        'polygon': '#8247E5',      # Polygon Purple
                        'litecoin': '#345D9D',     # Litecoin Blue
                        'chainlink': '#2A5ADA',    # Chainlink Blue
                        'uniswap': '#FF007A',      # Uniswap Pink
                        'stellar': '#000000',      # Stellar Black
                        'cosmos': '#2E3148',       # Cosmos Dark Blue
                        'monero': '#FF6600',       # Monero Orange
                        'tron': '#EF0027',         # Tron Red
                        'eos': '#000000',          # EOS Black
                        'tezos': '#2C7DF7',        # Tezos Blue
                        'vechain': '#15BDFF',      # VeChain Light Blue
                        'theta': '#2AB8E6'         # Theta Cyan
                    }
                    
                    # Fallback colors if crypto not in palette
                    fallback_colors = [
                        '#0EA5E9', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444',
                        '#06B6D4', '#EC4899', '#6366F1', '#14B8A6', '#F97316'
                    ]
                    
                    fig_pulse = go.Figure()
                    
                    for idx, symbol in enumerate(df_norm['symbol'].unique()):
                        symbol_data = df_norm[df_norm['symbol'] == symbol]
                        
                        # Get color from palette or use fallback
                        color = crypto_colors.get(symbol.lower(), fallback_colors[idx % len(fallback_colors)])
                        
                        fig_pulse.add_trace(go.Scatter(
                            x=symbol_data['timestamp'],
                            y=symbol_data['norm_price'],
                            name=symbol.upper(),
                            mode='lines',
                            line=dict(width=3, color=color),
                            hovertemplate=f'<b>{symbol.upper()}</b><br>%{{y:.3f}}%<extra></extra>'
                        ))
                    
                    fig_pulse.update_layout(**create_plot_layout("", 450))
                    fig_pulse.update_yaxes(title_text="Performance (%)")
                    fig_pulse.update_xaxes(title_text="Time")
                    st.plotly_chart(fig_pulse, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # === DETAILED TABLE ===
                    st.markdown("### 📋 Detailed Market Overview")
                    
                    col_table, col_viz = st.columns([2.5, 1.5])
                    
                    with col_table:
                        def get_sparkline(prices):
                            return prices.tail(60).tolist()
                        
                        sparklines = df_raw.groupby('symbol')['price'].apply(get_sparkline)
                        market_overview = latest.set_index('symbol')
                        market_overview['Price Trend'] = sparklines
                        
                        volume_sparklines = df_raw.groupby('symbol')['volume'].apply(get_sparkline)
                        market_overview['Volume Trend'] = volume_sparklines
                        
                        display_cols = market_overview[['price', 'price_change_24h', 'volume', 'Price Trend', 'Volume Trend']]
                        
                        st.dataframe(
                            display_cols,
                            column_config={
                                "price": st.column_config.NumberColumn("💵 Price (USD)", format="$%.6f"),
                                "price_change_24h": st.column_config.NumberColumn("📊 24h Change", format="%.3f%%"),
                                "volume": st.column_config.NumberColumn("📦 Volume", format="$%d"),
                                "Price Trend": st.column_config.LineChartColumn(
                                    "📈 Price Trend (60 ticks)",
                                    y_min=None,
                                    y_max=None
                                ),
                                "Volume Trend": st.column_config.LineChartColumn(
                                    "📊 Volume Activity",
                                    y_min=None,
                                    y_max=None
                                )
                            },
                            use_container_width=True,
                            height=400
                        )
                    
                    with col_viz:
                        st.markdown("**Volume Distribution**")
                        fig_pie = px.pie(
                            latest, 
                            values='volume', 
                            names='symbol',
                            hole=0.4,
                            color_discrete_sequence=px.colors.sequential.Blues_r
                        )
                        fig_pie.update_layout(
                            height=250,
                            margin=dict(l=0, r=0, t=0, b=0),
                            showlegend=True,
                            paper_bgcolor='white',
                            legend=dict(font=dict(size=10))
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
                        
                        st.markdown("**24h Change**")
                        fig_bar = px.bar(
                            latest.sort_values('price_change_24h'),
                            y='symbol',
                            x='price_change_24h',
                            orientation='h',
                            color='price_change_24h',
                            color_continuous_scale=['#ef4444', '#fbbf24', '#10b981']
                        )
                        fig_bar.update_layout(
                            height=250,
                            margin=dict(l=0, r=0, t=0, b=0),
                            paper_bgcolor='white',
                            plot_bgcolor='#f8fafc',
                            showlegend=False,
                            xaxis_title="",
                            yaxis_title=""
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # === INDIVIDUAL ANALYSIS ===
                    st.markdown("### 🔬 Individual Coin Analysis")
                    
                    all_symbols = sorted(df_raw['symbol'].unique().tolist())
                    selected_coins = st.multiselect(
                        "Select cryptocurrencies for detailed analysis:",
                        all_symbols,
                        default=all_symbols[:2] if len(all_symbols) >= 2 else all_symbols
                    )
                    
                    if selected_coins:
                        cols = st.columns(2)
                        for i, symbol in enumerate(selected_coins):
                            coin_data = df_raw[df_raw['symbol'] == symbol].copy()
                            
                            if not coin_data.empty:
                                with cols[i % 2]:
                                    st.markdown(f"""
                                    <div class='info-card'>
                                        <h4 style='color: #0369a1; margin: 0 0 1rem 0;'>
                                            {symbol.upper()} - Price & Volume
                                        </h4>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Metrics
                                    c1, c2, c3 = st.columns(3)
                                    c1.metric("Price", f"${coin_data['price'].iloc[-1]:.4f}")
                                    c2.metric("24h", f"{coin_data['price_change_24h'].iloc[-1]:.2f}%")
                                    c3.metric("Points", len(coin_data))
                                    
                                    # Chart
                                    fig = make_subplots(
                                        rows=2, cols=1,
                                        shared_xaxes=True,
                                        vertical_spacing=0.03,
                                        row_heights=[0.7, 0.3]
                                    )
                                    
                                    fig.add_trace(
                                        go.Scatter(
                                            x=coin_data['timestamp'],
                                            y=coin_data['price'],
                                            name='Price',
                                            line=dict(color='#0ea5e9', width=2),
                                            fill='tozeroy',
                                            fillcolor='rgba(14, 165, 233, 0.1)'
                                        ),
                                        row=1, col=1
                                    )
                                    
                                    fig.add_trace(
                                        go.Bar(
                                            x=coin_data['timestamp'],
                                            y=coin_data['volume'],
                                            name='Volume',
                                            marker_color='#06b6d4'
                                        ),
                                        row=2, col=1
                                    )
                                    
                                    fig.update_layout(**create_plot_layout("", 350))
                                    st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.info("⏳ Waiting for data from Kafka producer. Make sure the producer is running.")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# ==========================================
# TAB 2: REAL-TIME STREAM
# ==========================================
with tab2:
    st.markdown("<h2 style='margin-bottom: 1.5rem;'>🔥 Real-Time Data Streaming</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        stream_duration = st.slider("Stream duration (seconds):", 5, 60, 15)
    with col2:
        start_stream = st.button("▶️ Start Stream", use_container_width=True)
    
    if start_stream:
        st.markdown("### 📡 Live Stream Active")
        
        chart_placeholder = st.empty()
        metrics_placeholder = st.empty()
        data_placeholder = st.empty()
        
        try:
            consumer = KafkaConsumer(
                'crypto_raw',
                bootstrap_servers=KAFKA_BOOTSTRAP,
                auto_offset_reset='latest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                consumer_timeout_ms=stream_duration * 1000
            )
            
            stream_data = []
            message_count = 0
            
            for message in consumer:
                stream_data.append(message.value)
                message_count += 1
                
                if len(stream_data) > 0:
                    df_stream = pd.DataFrame(stream_data)
                    df_stream['timestamp'] = pd.to_datetime(df_stream['timestamp'])
                    
                    with metrics_placeholder.container():
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("📨 Messages", message_count)
                        m2.metric("🪙 Unique Coins", df_stream['symbol'].nunique())
                        m3.metric("⏱️ Latest Price", f"${df_stream['price'].iloc[-1]:.4f}")
                        m4.metric("📊 Avg Change", f"{df_stream['price_change_24h'].mean():.2f}%")
                    
                    with chart_placeholder.container():
                        fig_stream = px.scatter(
                            df_stream,
                            x='timestamp',
                            y='price',
                            color='symbol',
                            size='volume',
                            title="Live Price Updates"
                        )
                        fig_stream.update_layout(**create_plot_layout("Live Price Updates", 400))
                        st.plotly_chart(fig_stream, use_container_width=True)
                    
                    with data_placeholder.container():
                        st.markdown("### 📊 Latest Messages")
                        st.dataframe(df_stream.tail(10), use_container_width=True)
            
            consumer.close()
            st.success(f"✅ Stream completed! Processed {message_count} messages.")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# ==========================================
# TAB 3: ANOMALY DETECTION
# ==========================================
with tab3:
    st.markdown("<h2 style='margin-bottom: 1.5rem;'>⚠️ Anomaly Detection System</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("📡 Monitoring `crypto_alerts` topic for anomalies detected by Spark")
    with col2:
        check_alerts = st.button("🔍 Check Alerts", use_container_width=True)
    
    if check_alerts or auto_refresh:
        with st.spinner("🔍 Scanning for anomalies..."):
            try:
                consumer_alerts = KafkaConsumer(
                    'crypto_alerts',
                    bootstrap_servers=KAFKA_BOOTSTRAP,
                    auto_offset_reset='earliest',
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                    consumer_timeout_ms=2000
                )
                
                alerts = [m.value for m in consumer_alerts]
                consumer_alerts.close()
                
                if alerts:
                    df_alerts = pd.DataFrame(alerts)
                    df_alerts['timestamp'] = pd.to_datetime(df_alerts.get('timestamp', pd.Timestamp.now()))
                    
                    # === METRICS ===
                    st.markdown("### 🚨 Alert Summary")
                    m1, m2, m3, m4 = st.columns(4)
                    
                    total_alerts = len(df_alerts)
                    critical_alerts = len(df_alerts[df_alerts['anomaly_score'] > 5]) if 'anomaly_score' in df_alerts else 0
                    avg_score = df_alerts['anomaly_score'].mean() if 'anomaly_score' in df_alerts else 0
                    affected_coins = df_alerts['symbol'].nunique()
                    
                    m1.metric("🔔 Total Alerts", total_alerts)
                    m2.metric("🔥 Critical (>5σ)", critical_alerts)
                    m3.metric("📊 Avg Severity", f"{avg_score:.2f}")
                    m4.metric("🪙 Affected", affected_coins)
                    
                    st.markdown("---")
                    
                    # === VISUALIZATIONS ===
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### 📊 Severity by Coin")
                        if 'anomaly_score' in df_alerts:
                            fig_sev = px.bar(
                                df_alerts,
                                x='symbol',
                                y='anomaly_score',
                                color='anomaly_score',
                                color_continuous_scale=['#10b981', '#fbbf24', '#ef4444']
                            )
                            fig_sev.update_layout(**create_plot_layout("", 350))
                            st.plotly_chart(fig_sev, use_container_width=True)
                    
                    with col2:
                        st.markdown("#### 🕒 Timeline")
                        fig_time = px.scatter(
                            df_alerts,
                            x='timestamp',
                            y='symbol',
                            size='anomaly_score' if 'anomaly_score' in df_alerts else None,
                            color='anomaly_score' if 'anomaly_score' in df_alerts else 'symbol',
                            color_continuous_scale=['#10b981', '#fbbf24', '#ef4444']
                        )
                        fig_time.update_layout(**create_plot_layout("", 350))
                        st.plotly_chart(fig_time, use_container_width=True)
                    
                    # === GAUGES ===
                    st.markdown("#### 🎯 Real-Time Anomaly Metrics")
                    gauge_cols = st.columns(3)
                    
                    latest_alerts = df_alerts.nlargest(3, 'anomaly_score') if 'anomaly_score' in df_alerts else df_alerts.head(3)
                    
                    for idx, (i, alert) in enumerate(latest_alerts.iterrows()):
                        with gauge_cols[idx % 3]:
                            symbol = alert.get('symbol', 'Unknown')
                            score = alert.get('anomaly_score', 0)
                            fig_gauge = create_modern_gauge(
                                value=abs(score),
                                title=f"{symbol.upper()}",
                                min_val=0,
                                max_val=10,
                                threshold=3
                            )
                            st.plotly_chart(fig_gauge, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # === TABLE ===
                    st.markdown("#### 📋 Alert Log")
                    st.dataframe(
                        df_alerts.sort_values('anomaly_score' if 'anomaly_score' in df_alerts else df_alerts.columns[0], ascending=False),
                        use_container_width=True,
                        height=300
                    )
                    
                else:
                    st.success("✅ All Clear! No anomalies detected.")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# ==========================================
# TAB 4: ML PERFORMANCE
# ==========================================
with tab4:
    st.markdown("<h2 style='margin-bottom: 1.5rem;'>🤖 Machine Learning Performance</h2>", unsafe_allow_html=True)
    
    try:
        mlflow.set_tracking_uri(MLFLOW_URI)
        client = MlflowClient()
        
        experiments = client.search_experiments()
        all_runs = []
        
        for exp in experiments:
            runs = client.search_runs(exp.experiment_id)
            for run in runs:
                run_data = {
                    "Run ID": run.info.run_id[:8],
                    "Experiment": exp.name,
                    "Run Name": run.data.tags.get("mlflow.runName", "Unnamed"),
                    "Model": run.data.params.get("model_type", "Unknown"),
                    "Status": run.info.status,
                    "Start Time": pd.to_datetime(run.info.start_time, unit="ms"),
                    "Duration": (run.info.end_time - run.info.start_time) / 1000 if run.info.end_time else None
                }
                
                for k, v in run.data.metrics.items():
                    run_data[k] = v
                
                all_runs.append(run_data)
        
        if all_runs:
            df_runs = pd.DataFrame(all_runs)
            df_runs = df_runs.sort_values("Start Time", ascending=False)
            
            # === METRICS ===
            st.markdown("### 📊 Performance Overview")
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric("🏃 Total Runs", len(df_runs))
            col2.metric("⏱️ Avg Duration", f"{df_runs['Duration'].mean():.1f}s" if 'Duration' in df_runs else "N/A")
            col3.metric("🎯 Best AUC", f"{df_runs['auc'].max():.4f}" if 'auc' in df_runs else "N/A")
            col4.metric("🧪 Experiments", df_runs['Experiment'].nunique())
            
            st.markdown("---")
            
            # === CHARTS ===
            st.markdown("### 📈 Model Comparison")
            col1, col2 = st.columns(2)
            
            with col1:
                if 'auc' in df_runs.columns:
                    fig_auc = px.box(
                        df_runs,
                        x='Model',
                        y='auc',
                        color='Model',
                        points="all"
                    )
                    fig_auc.update_layout(**create_plot_layout("AUC Score by Model", 350))
                    st.plotly_chart(fig_auc, use_container_width=True)
            
            with col2:
                if 'auc' in df_runs.columns:
                    fig_prog = px.line(
                        df_runs.sort_values('Start Time'),
                        x='Start Time',
                        y='auc',
                        color='Model',
                        markers=True
                    )
                    fig_prog.update_layout(**create_plot_layout("Progress Over Time", 350))
                    st.plotly_chart(fig_prog, use_container_width=True)
            
            st.markdown("---")
            
            # === TABLE ===
            st.markdown("### 📊 Training History")
            st.dataframe(df_runs, use_container_width=True, height=400)
            
        else:
            st.warning("⚠️ No training runs found.")
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# ==========================================
# TAB 5: PREDICTIONS
# ==========================================
with tab5:
    st.markdown("<h2 style='margin-bottom: 1.5rem;'>🎯 AI Prediction Center</h2>", unsafe_allow_html=True)
    
    pred_type = st.radio(
        "Select prediction task:",
        ["📈 Trend Prediction", "⚠️ Anomaly Detection"],
        horizontal=True
    )
    
    st.markdown("---")
    
    if pred_type == "📈 Trend Prediction":
        st.markdown("### 📈 Price Trend Forecasting")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Input Features")
            
            pred_price = st.number_input("Current Price ($):", value=50000.0, step=100.0)
            pred_ma = st.number_input("Moving Average ($):", value=49800.0, step=100.0)
            pred_vol = st.number_input("Volatility (%):", value=2.5, step=0.1)
        
        with col2:
            st.markdown("#### 🎯 Results")
            
            if st.button("🚀 Predict", use_container_width=True):
                momentum = (pred_price - pred_ma) / pred_ma * 100
                
                if momentum > 1.0:
                    prediction = "UP 📈"
                    confidence = min(75 + abs(momentum) * 2, 95)
                    color = "#10b981"
                elif momentum < -1.0:
                    prediction = "DOWN 📉"
                    confidence = min(75 + abs(momentum) * 2, 95)
                    color = "#ef4444"
                else:
                    prediction = "NEUTRAL ➡️"
                    confidence = 55
                    color = "#fbbf24"
                
                st.markdown(f"""
                <div style='background: white; padding: 30px; border-radius: 15px; 
                            border: 3px solid {color}; text-align: center;
                            box-shadow: 0 4px 20px rgba(14, 165, 233, 0.15);'>
                    <h1 style='color: {color}; font-size: 2.5rem; margin: 0;'>{prediction}</h1>
                    <p style='color: #0c4a6e; font-size: 1.3rem; margin-top: 10px;'>
                        Confidence: {confidence:.1f}%
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                fig_gauge = create_modern_gauge(
                    value=confidence,
                    title="Confidence Level",
                    min_val=0,
                    max_val=100,
                    threshold=70
                )
                st.plotly_chart(fig_gauge, use_container_width=True)
    
    else:  # Anomaly
        st.markdown("### ⚠️ Anomaly Detection")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Market Conditions")
            
            anom_price = st.number_input("Price ($):", value=50000.0, step=100.0)
            anom_ma = st.number_input("MA ($):", value=49800.0, step=100.0)
            anom_std = st.number_input("Std Dev:", value=250.0, step=10.0)
        
        with col2:
            st.markdown("#### 🎯 Analysis")
            
            if st.button("🔍 Detect", use_container_width=True):
                z_score = (anom_price - anom_ma) / anom_std if anom_std > 0 else 0
                
                if abs(z_score) > 5:
                    status = "🔴 CRITICAL"
                    color = "#ef4444"
                elif abs(z_score) > 3:
                    status = "🟡 WARNING"
                    color = "#fbbf24"
                else:
                    status = "🟢 NORMAL"
                    color = "#10b981"
                
                st.markdown(f"""
                <div style='background: white; padding: 30px; border-radius: 15px; 
                            border: 3px solid {color}; text-align: center;
                            box-shadow: 0 4px 20px rgba(14, 165, 233, 0.15);'>
                    <h1 style='color: {color}; font-size: 2.5rem; margin: 0;'>{status}</h1>
                    <p style='color: #0c4a6e; font-size: 1.3rem; margin-top: 10px;'>
                        Z-Score: {z_score:.2f}σ
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                fig_gauge = create_modern_gauge(
                    value=abs(z_score),
                    title="Anomaly Score",
                    min_val=0,
                    max_val=10,
                    threshold=3
                )
                st.plotly_chart(fig_gauge, use_container_width=True)

# ==========================================
# FOOTER
# ==========================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 1.5rem; background: white; border-radius: 12px;
            box-shadow: 0 2px 12px rgba(14, 165, 233, 0.08);'>
    <p style='margin: 0; color: #0369a1; font-size: 0.95rem; font-weight: 600;'>
        💎 Powered by <strong>Apache Kafka</strong> • <strong>Apache Spark</strong> • <strong>HDFS</strong> • <strong>MLflow</strong>
    </p>
    <p style='margin: 0.5rem 0 0 0; color: #64748b; font-size: 0.85rem;'>
        Real-Time Crypto Intelligence Platform | Built with Streamlit
    </p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh
if auto_refresh:
    import time
    time.sleep(30)
    st.rerun()