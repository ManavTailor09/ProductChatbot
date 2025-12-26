# ProductChatbot_openai.py
# -----------------------------------------------------------
# LIVE AI SHOPPING CHATBOT (FULL FIXED VERSION)
# - Latest OpenAI API
# - SerpApi via HTTP (no import errors)
# - PERFECT SHOPPING CART (qty + remove + total)
# - Login + AI + History
# -----------------------------------------------------------

import os
import streamlit as st
import requests
from urllib.parse import quote_plus
from dotenv import load_dotenv
from openai import OpenAI

# -----------------------------------------------------------
# LOAD ENV
# -----------------------------------------------------------
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

if not OPENAI_API_KEY:
    st.error("❌ Missing OPENAI_API_KEY in .env")
    st.stop()

if not SERPAPI_API_KEY:
    st.error("❌ Missing SERPAPI_API_KEY in .env")
    st.stop()

# Set environment variable (backup)
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Initialize OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)


# -----------------------------------------------------------
# UTILS
# -----------------------------------------------------------
def product_image_url(name):
    """Generate placeholder image."""
    txt = quote_plus(name[:30])
    return f"https://via.placeholder.com/500x300.png?text={txt}"


def convert_price_to_int(price):
    """Convert ₹12,999 → 12999"""
    if not price:
        return 0
    digits = ''.join([c for c in price if c.isdigit()])
    return int(digits) if digits else 0


# -----------------------------------------------------------
# SHOPPING SEARCH - SERPAPI (HTTP)
# -----------------------------------------------------------
def serpapi_shopping(query, num=8):
    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "hl": "en",
        "gl": "in",
        "num": num,
    }

    try:
        res = requests.get(url, params=params).json()
    except:
        return []

    items = res.get("shopping_results", [])
    results = []

    for item in items[:num]:
        results.append({
            "title": item.get("title"),
            "price": convert_price_to_int(item.get("price", "")),
            "price_str": item.get("price", ""),
            "source": item.get("source"),
            "link": item.get("link"),
            "thumb": item.get("thumbnail"),
            "snippet": item.get("snippet") or item.get("description")
        })

    return results


# -----------------------------------------------------------
# OPENAI SMART REPLY
# -----------------------------------------------------------
def openai_reply(username, query, results, history):

    evidence = []
    for i, r in enumerate(results):
        evidence.append(
            f"{i+1}. {r['title']} | ₹{r['price']} | {r['source']}"
        )

    evidence_text = "\n".join(evidence) if evidence else "No results found."
    recent = "\n".join([h["user"] for h in history[-3:]]) if history else "None"

    system_prompt = (
        "You are a friendly Indian shopping assistant. "
        "Use Hinglish (Hindi + English). "
        "Call the user '<username> bhai'. "
        "Recommend best 3 products + 2 alternatives. "
        "Use live product evidence. "
        "End with: 'Bhai bolo next kya compare karna hai?'"
    )

    user_prompt = f"""
User Name: {username}
Query: {query}

Live Products:
{evidence_text}

Recent Searches:
{recent}
"""

    try:
        ai = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=350,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        return ai.choices[0].message.content

    except Exception as e:
        return f"⚠️ AI Error: {e}"


# -----------------------------------------------------------
# STREAMLIT SESSION STATE
# -----------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = ""

if "history" not in st.session_state:
    st.session_state.history = []

if "cart" not in st.session_state:
    st.session_state.cart = []   # [{title, price, qty, link}]

if "recommendation_count" not in st.session_state:
    st.session_state.recommendation_count = 0


# -----------------------------------------------------------
# LOGIN PAGE
# -----------------------------------------------------------
if not st.session_state.logged_in:
    st.title("🔐 Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u.strip() != "" and p.strip() != "":
            st.session_state.logged_in = True
            st.session_state.user = u
            st.success(f"Welcome {u} bhai! 😎")
            st.rerun()
        else:
            st.error("Enter username & password")

    st.stop()


# -----------------------------------------------------------
# CART FUNCTIONS
# -----------------------------------------------------------
def add_to_cart(item):
    for c in st.session_state.cart:
        if c["title"] == item["title"]:
            c["qty"] += 1
            return

    st.session_state.cart.append({
        "title": item["title"],
        "price": item["price"],
        "qty": 1,
        "link": item["link"]
    })


def increase_qty(idx):
    st.session_state.cart[idx]["qty"] += 1


def decrease_qty(idx):
    if st.session_state.cart[idx]["qty"] > 1:
        st.session_state.cart[idx]["qty"] -= 1
    else:
        st.session_state.cart.pop(idx)


def remove_item(idx):
    st.session_state.cart.pop(idx)


# -----------------------------------------------------------
# SIDEBAR (CART + ACCOUNT)
# -----------------------------------------------------------
with st.sidebar:
    st.title("🛒 Shopping Cart")

    if not st.session_state.cart:
        st.write("Cart is empty.")
    else:
        total = 0

        for i, item in enumerate(st.session_state.cart):
            st.markdown(f"### {item['title']}")
            st.write(f"Price: ₹{item['price']:,}")
            st.write(f"Qty: {item['qty']}")
            st.write(f"[Open Product]({item['link']})")

            c1, c2, c3 = st.columns(3)

            with c1:
                if st.button("➕", key=f"inc{i}"):
                    increase_qty(i)
                    st.rerun()

            with c2:
                if st.button("➖", key=f"dec{i}"):
                    decrease_qty(i)
                    st.rerun()

            with c3:
                if st.button("🗑 Remove", key=f"rem{i}"):
                    remove_item(i)
                    st.rerun()

            st.markdown("---")

            total += item["price"] * item["qty"]

        st.subheader(f"Total: ₹{total:,}")

        if st.button("Clear Cart"):
            st.session_state.cart = []
            st.rerun()

    st.markdown("---")
    st.write(f"Logged in as: **{st.session_state.user}**")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()


# -----------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------
st.title("🛒 Live AI Product Recommendation Chatbot")
st.caption("Real-time Internet Shopping + AI Recommendations")

query = st.text_input("Search any product (e.g., best phone under 30000)")


if st.button("Search") and query.strip() != "":
    st.info("Searching live internet results...")

    with st.spinner("Fetching products..."):
        products = serpapi_shopping(query)

    st.success(f"Found {len(products)} items!")

    with st.spinner("AI analyzing..."):
        reply = openai_reply(st.session_state.user, query, products, st.session_state.history)

    st.markdown("### 🤖 AI Assistant Reply")
    st.write(reply)

    st.session_state.history.append({"user": query})

    if products:
        st.session_state.recommendation_count += 1

    st.markdown("### 📦 Products Found")
    cols = st.columns(2)

    for i, p in enumerate(products):
        col = cols[i % 2]

        with col:
            st.image(p["thumb"] or product_image_url(p["title"]), use_column_width=True)
            st.markdown(f"**{p['title']}**")
            st.write(f"Price: ₹{p['price']:,}")
            st.write(f"Store: {p['source']}")

            if st.button("Add to Cart", key=f"add{i}"):
                add_to_cart(p)
                st.toast("Added to cart!")
                st.rerun()


# FOOTER
st.markdown("---")
st.write("Built with ❤️ using OpenAI + SerpApi + Streamlit")
