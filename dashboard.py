import streamlit as st
import pandas as pd

st.set_page_config(page_title="Ox Alpha Trade Agent", layout="wide")
st.title("🤖 Ox Alpha — Trade Analysis Dashboard")

try:
    df = pd.read_csv('logs/signals.csv')
except FileNotFoundError:
    st.warning("No signals yet — wait for the first agent run.")
    st.stop()

df = df.sort_values('time', ascending=False)
st.subheader("Latest signals")
verdict_filter = st.multiselect("Filter", ['BUY','SELL','WAIT'], default=['BUY','SELL'])
st.dataframe(df[df['verdict'].isin(verdict_filter)].head(50), use_container_width=True)

c1, c2, c3 = st.columns(3)
c1.metric("Total BUY signals", len(df[df.verdict=='BUY']))
c2.metric("Total SELL signals", len(df[df.verdict=='SELL']))
c3.metric("Avg win rate (backtested)", f"{pd.to_numeric(df.win_rate, errors='coerce').mean():.1f}%")

st.subheader("🔥 Highest-confidence recent setups")
best = df[df['verdict'] != 'WAIT'].copy()
best['confidence'] = pd.to_numeric(best['confidence'], errors='coerce')
st.dataframe(best.sort_values('confidence', ascending=False).head(15), use_container_width=True)


st.subheader("Win rate by timeframe")
st.bar_chart(df.groupby('tf')['win_rate'].astype(float).mean())
