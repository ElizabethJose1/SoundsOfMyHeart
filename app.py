import streamlit as st
import requests
from dotenv import load_dotenv
import os
import pandas as pd

# Load credentials from .env file
load_dotenv()
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")

def get_spotify_token():
    """Requests an access token from Spotify using Client Credentials flow."""
    auth_url = "https://accounts.spotify.com/api/token"
    response = requests.post(auth_url, {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    if response.status_code != 200:
        st.error("Failed to authenticate with Spotify. Check your credentials.")
        return None
    token = response.json()["access_token"]
    return token

# Title with heart decoration on sides
st.markdown("""
<div style='display: flex; align-items: center; justify-content: center; gap: 20px;'>
    <svg width="180" height="60" viewBox="0 0 180 60">
        <polyline points="0,30 20,30 30,10 40,50 50,10 60,50 70,30 90,30 100,15 110,45 120,15 130,45 140,30 180,30"
                  fill="none" stroke="#6A4C93" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    <h1 style='margin: 0; white-space: nowrap;'> Sounds of My Heart</h1>
    <svg width="180" height="60" viewBox="0 0 180 60">
        <polyline points="0,30 20,30 30,10 40,50 50,10 60,50 70,30 90,30 100,15 110,45 120,15 130,45 140,30 180,30"
                  fill="none" stroke="#E63946" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
</div>
""", unsafe_allow_html=True)

# Small description
st.markdown(
    "<p style='text-align: center; font-size: 20px;'>Discover music that speaks to you! Search for artists and tracks, or find out where they're playing live next.</p>",
    unsafe_allow_html=True
)
token = get_spotify_token()

# CSS for landing page buttons
st.markdown("""
<style>
.st-key-landing_buttons div.stButton > button {
    height: 150px;
    width: 100%;
    border-radius: 16px;
    border: none;
    white-space: normal;
}
.st-key-landing_buttons div.stButton > button p {
    font-size: 32px !important;
    font-weight: bold !important;
}
.st-key-landing_buttons div.stButton > button[kind="primary"] {
    background-color: #470906 !important;
    color: white !important;
}
.st-key-landing_buttons div.stButton > button[kind="secondary"] {
    background-color: #2F0647 !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# Initialize which section is open
if "view" not in st.session_state:
    st.session_state.view = None

with st.container(key="landing_buttons"):
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        if st.button(" Search Artists & Tracks", use_container_width=True, type="primary"):
            st.session_state.view = "search"
    with col2:
        if st.button(" Find Tour Dates", use_container_width=True, type="secondary"):
            st.session_state.view = "tour"

# --- Search Section ---
if st.session_state.view == "search":
    st.subheader("🔍 Search for an Artist or Track")

    search_type = st.radio("Search for:", ["artist", "track"], horizontal=True)
    search_query = st.text_input(f"Enter an {search_type} name" if search_type == "artist" else "Enter a song name")

    with st.expander("Advanced Filters"):
        use_year_filter = st.checkbox("Filter by release year", key="year_filter_toggle")

        if use_year_filter:
            min_year = st.slider(
                "Show tracks released in the year:",
                min_value=1950,
                max_value=2026,
                value=2000,
                key="year_filter_slider"
            )

        hide_explicit = st.checkbox("Hide explicit tracks", key="explicit_checkbox")

    search_clicked = st.button("Search")

    if search_clicked:
        if not search_query and not (search_type == "track" and use_year_filter):
            st.warning("Please enter something to search for, or enable the year filter.")
        else:
            if search_type == "track" and use_year_filter:
                if search_query:
                    query = f"{search_query} year:{min_year}"
                else:
                    query = f"year:{min_year}"
            else:
                query = search_query

            if token:
                headers = {"Authorization": f"Bearer {token}"}
                params = {
                    "q": query,
                    "type": search_type,
                    "limit": 10
                }
                response = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params)

                if response.status_code == 200:
                    data = response.json()
                    items = data[search_type + "s"]["items"]

                    if not items:
                        st.info("No results found. Try a different search.")
                    else:
                        if search_type == "artist":
                            results = [{
                                "Name": a.get("name", "Unknown"),
                                "Spotify Link": a.get("external_urls", {}).get("spotify", "")
                            } for a in items]
                        else:  # track
                            results = [{
                                "Track": t.get("name", "Unknown"),
                                "Artist": t.get("artists", [{}])[0].get("name", "Unknown"),
                                "Album": t.get("album", {}).get("name", "Unknown"),
                                "Release Date": t.get("album", {}).get("release_date", "N/A"),
                                "Duration (min)": round(t.get("duration_ms", 0) / 60000, 2),
                                "Explicit": "Yes" if t.get("explicit") else "No",
                                "Spotify Link": t.get("external_urls", {}).get("spotify", "")
                            } for t in items]

                        df = pd.DataFrame(results)
                        st.success(f"Found {len(results)} results!")

                        link_column = "Spotify Link" if "Spotify Link" in df.columns else None

                        st.dataframe(
                            df,
                            column_config={
                                "Spotify Link": st.column_config.LinkColumn("Spotify Link", display_text="Open in Spotify")
                            } if link_column else None
                        )

                        if search_type == "track" and not df.empty:
                            st.subheader(" Duration")
                            chart_df = df.set_index("Track")["Duration (min)"]
                            st.bar_chart(chart_df)
                else:
                    st.error(f"Spotify API error: {response.status_code}")

# --- Upcoming Tour Dates Map ---
elif st.session_state.view == "tour":
    st.subheader("🗺️ Find Upcoming Tour Dates")

    tour_search_type = st.radio("Search by:", ["artist", "city"], horizontal=True, key="tour_search_type")
    tour_query = st.text_input(
        "Enter an artist name" if tour_search_type == "artist" else "Enter a city name",
        key="tour_search_input"
    )

    if st.button("Find Tour Dates", key="tour_search_button"):
        if not tour_query:
            st.warning(f"Please enter a {tour_search_type} name.")
        else:
            tm_url = "https://app.ticketmaster.com/discovery/v2/events.json"
            tm_params = {
                "apikey": TICKETMASTER_API_KEY,
                "classificationName": "music",
                "size": 20
            }

            if tour_search_type == "artist":
                tm_params["keyword"] = tour_query
            else:
                tm_params["city"] = tour_query
            tm_response = requests.get(tm_url, params=tm_params)

            if tm_response.status_code == 200:
                tm_data = tm_response.json()

                if "_embedded" not in tm_data or "events" not in tm_data["_embedded"]:
                    st.info(f"No upcoming shows found for '{tour_query}'.")
                else:
                    events = tm_data["_embedded"]["events"]

                    event_rows = []
                    map_points = []

                    for e in events:
                        venue = e.get("_embedded", {}).get("venues", [{}])[0]
                        city = venue.get("city", {}).get("name", "Unknown")
                        venue_name = venue.get("name", "Unknown")
                        date = e.get("dates", {}).get("start", {}).get("localDate", "TBA")
                        lat = venue.get("location", {}).get("latitude")
                        lon = venue.get("location", {}).get("longitude")
                        url = e.get("url", "")

                        event_rows.append({
                            "Event": e.get("name", "Unknown"),
                            "Venue": venue_name,
                            "City": city,
                            "Date": date,
                            "Tickets": url
                        })

                        if lat and lon:
                            map_points.append({"lat": float(lat), "lon": float(lon)})

                    event_df = pd.DataFrame(event_rows)
                    st.success(f"Found {len(event_rows)} upcoming shows for {tour_query}!")
                    st.dataframe(
                        event_df,
                        column_config={
                            "Tickets": st.column_config.LinkColumn("Tickets", display_text="Buy Tickets")
                        }
                    )

                    if map_points:
                        map_df = pd.DataFrame(map_points)
                        st.map(map_df)
                    else:
                        st.info("No location data available to plot on the map.")
            else:
                st.error(f"Ticketmaster API error: {tm_response.status_code}")