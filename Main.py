# Zenless Collector

import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json, os

# --- constants ---
URL = "https://zenless-zone-zero.fandom.com/wiki/Redemption_Code"
UA = {"User-Agent":"Mozilla/5.0"}
CACHE_FILE = "cached_codes.json"

# Regex patterns
code_pattern = re.compile(r"\b[A-Z0-9]{6,24}\b")
poly_pattern = re.compile(r"(\d{1,4})\s*Polychrome[s]?", re.IGNORECASE)

date_formats = ["%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"]

# --- helper functions ---
def parse_date(txt):
    if not txt:
        return None
    txt_low = txt.lower()
    if "expired" in txt_low:
        return "EXPIRED"
    if any(x in txt_low for x in ["no expiry","none","—","-","tbd","unknown"]):
        return None
    txt_clean = re.sub(r"\[\d+\]","",txt).strip()
    for fmt in date_formats:
        try:
            return datetime.strptime(txt_clean, fmt).date()
        except:
            continue
    return None  # couldn't parse

def fetch_codes():
    try:
        r = requests.get(URL, headers=UA, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print("Error fetching page:", e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.select_one("table.wikitable")
    if not table:
        print("No table found on page!")
        return []

    today = datetime.today().date()
    codes = []

    for row in table.select("tbody tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        code_txt = cells[0].get_text(" ", strip=True)
        reward_txt = cells[1].get_text(" ", strip=True) if len(cells) > 1 else ""
        expiry_txt = cells[2].get_text(" ", strip=True) if len(cells) > 2 else ""

        # match code
        mcode = code_pattern.search(code_txt.upper())
        if not mcode:
            continue
        code = mcode.group(0)

        # check expiry
        expiry = parse_date(expiry_txt)
        if expiry == "EXPIRED":
            continue
        if isinstance(expiry, datetime):
            expiry = expiry.date()
        if expiry is not None and expiry < today:
            continue

        # find polychrome
        mp = poly_pattern.search(reward_txt)
        if not mp:
            continue
        poly = int(mp.group(1))
        if poly > 0:
            codes.append((code, poly))

    # remove duplicates (keep max poly)
    final_codes = {}
    for c,p in codes:
        if c in final_codes:
            final_codes[c] = max(p, final_codes[c])
        else:
            final_codes[c] = p

    # sort descending by poly
    return sorted(final_codes.items(), key=lambda x: -x[1])

# --- caching functions ---
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE,"r") as f:
            return json.load(f)
    return {}

def save_cache(data):
    with open(CACHE_FILE,"w") as f:
        json.dump(data,f)

# --- Streamlit UI ---
st.set_page_config(page_title="Zenless Zone Zero Codes", layout="centered")
st.title("Zenless Collector")
st.write("Fetch Active Redeem Codes For Polychrome!")

if st.button("Fetch Codes"):
    with st.spinner("Fetching Codes..."):
        codes = fetch_codes()
        cached = load_cache()

        new_codes = [c for c,p in codes if c not in cached]
        save_cache({c:p for c,p in codes})

        if codes:
            st.success(f"Found {len(codes)} Active Codes!")
            sort_order = st.selectbox("Sort Polychrome:", ["Descending","Ascending"])
            display = sorted(codes,key=lambda x:x[1], reverse=(sort_order=="Descending"))
            for c,p in display:
                st.write(f"**{c}** - {p} Polychrome")
                # simple copy-to-clipboard trick
                st.button("Copy",key=c,on_click=lambda c=c: st.experimental_set_query_params(copy=c))
            if new_codes:
                st.balloons()
                st.info(f"🎉 New Codes Detected: {', '.join(new_codes)}")
        else:
            st.warning("No Active Codes Found :(")


