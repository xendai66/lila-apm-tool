import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from PIL import Image

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="🎮 LILA BLACK: Player Journey Visualizer")

# --- MAP CONFIGS ---
MAP_CONFIGS = {
    'AmbroseValley': {'scale': 900, 'ox': -370, 'oz': -473, 'img': 'player_data/minimaps/AmbroseValley_Minimap.png'},
    'GrandRift': {'scale': 581, 'ox': -290, 'oz': -290, 'img': 'player_data/minimaps/GrandRift_Minimap.png'},
    'Lockdown': {'scale': 1000, 'ox': -500, 'oz': -500, 'img': 'player_data/minimaps/Lockdown_Minimap.jpg'}
}

base_path = os.path.dirname(__file__)

# --- FUNCTIONS ---
def map_to_pixel(x, z, map_id):
    conf = MAP_CONFIGS[map_id]
    u = (x - conf['ox']) / conf['scale']
    v = (z - conf['oz']) / conf['scale']
    pixel_x = u * 1024
    pixel_y = (1 - v) * 1024
    return pixel_x, pixel_y

def is_bot(user_id):
    return str(user_id).isdigit()

@st.cache_data
def load_match_data(day_folder, map_id):
    path = f"player_data/{day_folder}/"
    if not os.path.exists(path):
        return pd.DataFrame()
    all_dfs = []
    files = os.listdir(path)[:100]  # Limit for performance
    for f in files:
        try:
            df = pd.read_parquet(os.path.join(path, f))
            df['event'] = df['event'].apply(lambda x: x.decode('utf-8') if isinstance(x, bytes) else x)
            if df['map_id'].iloc[0] == map_id:
                df['is_bot'] = df['user_id'].apply(is_bot)
                df['px'], df['py'] = zip(*df.apply(lambda r: map_to_pixel(r['x'], r['z'], map_id), axis=1))
                all_dfs.append(df)
        except:
            continue
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

# --- UI SIDEBAR ---
st.title("🎮 LILA BLACK: Player Journey Tool")
st.sidebar.header("Filters")

selected_map = st.sidebar.selectbox("Select Map", list(MAP_CONFIGS.keys()), key='map_selector')
selected_day = st.sidebar.selectbox(
    "Select Date",
    ["February_10", "February_11", "February_12", "February_13", "February_14"],
    key='date_selector'
)

# --- LOAD DATA ---
df = load_match_data(selected_day, selected_map)

if df.empty:
    st.warning("No data found for the selected filters.")
    st.stop()

# --- Sidebar Options ---
st.sidebar.header("Visual Options")
show_heatmap = st.sidebar.checkbox("Show Kill/Death Heatmap", value=False, key='heatmap_toggle')
selected_match = st.sidebar.selectbox(
    "Select Match ID",
    df['match_id'].unique(),
    key='match_selector_unique'
)
match_df = df[df['match_id'] == selected_match].sort_values('ts')

# --- Timeline Slider ---
start_time = match_df['ts'].min()
match_df['seconds'] = (match_df['ts'] - start_time).dt.total_seconds()
max_seconds = int(match_df['seconds'].max())
if max_seconds <= 0:
    max_seconds = 1
    match_df['seconds'] = 0

st.session_state.setdefault('current_second', 0)
st.session_state.setdefault('playing', False)

st.sidebar.header("Animation Controls")
col1, col2, col3 = st.sidebar.columns(3)
if col1.button("⏮️ Restart"):
    st.session_state.current_second = 0
    st.session_state.playing = False
if col2.button("▶️ Play"):
    st.session_state.playing = True
if col3.button("⏸️ Pause"):
    st.session_state.playing = False

speed = st.sidebar.slider("Animation Speed (seconds per step)", 0.01, 1.0, 0.1, step=0.01)

st.session_state.current_second = st.sidebar.slider(
    "Timeline (seconds)",
    min_value=0,
    max_value=max_seconds,
    value=int(st.session_state.current_second),
    key='timeline_slider'
)

# --- Background Image ---
img_path = os.path.join(base_path, MAP_CONFIGS[selected_map]['img'])
if not os.path.exists(img_path):
    st.error(f"Map image not found: {img_path}")
    st.stop()
img = Image.open(img_path)
plot_placeholder = st.empty()

# --- Drawing Function ---
def draw_figure(current_df):
    fig = go.Figure()
    fig.add_layout_image(
        dict(source=img, xref="x", yref="y", x=0, y=1024,
             sizex=1024, sizey=1024, sizing="stretch", opacity=1, layer="below")
    )

    # Heatmap
    if show_heatmap:
        combat_df = df[df['event'].str.contains('Kill|Death', case=False, na=False)]
        if not combat_df.empty:
            fig.add_trace(go.Histogram2dContour(
                x=combat_df['px'], y=combat_df['py'],
                colorscale='YlOrRd', opacity=0.4, showlegend=False, ncontours=20
            ))

    # Player Paths
    for uid in current_df['user_id'].unique():
        p_df = current_df[current_df['user_id'] == uid]
        color = "blue" if not p_df['is_bot'].iloc[0] else "orange"
        label = "Human" if not p_df['is_bot'].iloc[0] else "Bot"
        fig.add_trace(go.Scatter(
            x=p_df['px'], y=p_df['py'], mode='lines',
            line=dict(color=color, width=2),
            name=f"{label}: {str(uid)[:5]}",
            hoverinfo='text', text=p_df['event']
        ))

    # Event Markers (human vs bot)
    event_types = {
        'Kill': {'human_color': 'green', 'bot_color': 'red', 'symbol': 'x', 'size': 12},
        'Death': {'human_color': 'blue', 'bot_color': 'black', 'symbol': 'triangle-down', 'size': 12},
        'Loot': {'human_color': 'gold', 'bot_color': 'orange', 'symbol': 'diamond', 'size': 10},
        'Storm': {'human_color': 'purple', 'bot_color': 'brown', 'symbol': 'circle', 'size': 10}
    }

    for e_name, e_style in event_types.items():
        e_df = current_df[current_df['event'].str.contains(e_name, case=False, na=False)]
        if not e_df.empty:
            human_df = e_df[~e_df['is_bot']]
            bot_df = e_df[e_df['is_bot']]
            if not human_df.empty:
                fig.add_trace(go.Scatter(
                    x=human_df['px'], y=human_df['py'], mode='markers',
                    marker=dict(color=e_style['human_color'], symbol=e_style['symbol'], size=e_style['size']),
                    name=f"Human {e_name}"
                ))
            if not bot_df.empty:
                fig.add_trace(go.Scatter(
                    x=bot_df['px'], y=bot_df['py'], mode='markers',
                    marker=dict(color=e_style['bot_color'], symbol=e_style['symbol'], size=e_style['size']),
                    name=f"Bot {e_name}"
                ))

    fig.update_xaxes(range=[0, 1024], visible=False)
    fig.update_yaxes(range=[0, 1024], visible=False)
    fig.update_layout(width=900, height=900, margin=dict(l=0, r=0, t=50, b=0),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# --- Update Animation ---
if st.session_state.playing and st.session_state.current_second < max_seconds:
    st.session_state.current_second += 1

display_df = match_df[match_df['seconds'] <= st.session_state.current_second]
fig = draw_figure(display_df)
plot_placeholder.plotly_chart(fig, use_container_width=True, key=f'plot_{st.session_state.current_second}')

# --- Legend Info ---
st.sidebar.markdown("**Legend:**")
st.sidebar.markdown("""
- **Human Path:** Blue
- **Bot Path:** Orange
- **Human Kill:** Green X
- **Bot Kill:** Red X
- **Human Death:** Blue Triangle-Down
- **Bot Death:** Black Triangle-Down
- **Human Loot:** Gold Diamond
- **Bot Loot:** Orange Diamond
- **Storm:** Purple/Brown Circle
""")