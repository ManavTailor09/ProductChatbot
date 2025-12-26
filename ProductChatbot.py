# ProductChatbot.py
# ---------------------------------------------
# 🛒 SMART PRODUCT CHATBOT – STREAMLIT UI (PRO + VOICE + LOGIN + COUNTER + PERSONAL)
# Features:
# - Proper login (username + password)
# - Personal replies using username (e.g. "Manav bhai...")
# - Uses previous searches for smarter recommendations
# - "Aaj ka special deal" highlight
# - Chat-style product search
# - Brand + category + price filters
# - "Similar to <product>" recommendations
# - Product cards with images
# - Add to Cart + total
# - Voice input helper (upload audio -> text)
# - Recommendation counter (kitni baar list dikhayi)
# Uses mega_real_product_dataset.csv in same folder
# ---------------------------------------------

import streamlit as st
import pandas as pd
import re
import random
from urllib.parse import quote_plus

# Voice libraries
import speech_recognition as sr
from io import BytesIO
from pydub import AudioSegment

# ---------- USER LOGIN CONFIG ----------
# Simple hard-coded users. You can change / add.
USERS = {
    "admin": "admin123",
    "manav": "manav123",
    "user": "user123"
}

# ---------- LOAD DATA ----------
@st.cache_data
def load_data():
    df = pd.read_csv("mega_real_product_dataset.csv")
    df["name_lower"] = df["product_name"].str.lower()
    df["cat_lower"] = df["category"].str.lower()
    return df

df = load_data()

# ---------- CONFIG ----------
BRANDS = [
    "samsung","iphone","apple","xiaomi","redmi","realme","oneplus",
    "vivo","oppo","iqoo","tecno","moto","nokia",
    "hp","dell","asus","lenovo","acer","msi","microsoft","infinix",
    "nike","adidas","levis","zara","puma","h&m","woodland","us polo",
    "biba","ray-ban","wildcraft","jockey","casio","titan","fossil",
    "ikea","godrej","nilkamal",
    "prestige","milton","cello","bajaj","whirlpool","havells","philips",
    "kent","faber","kutchina",
    "tata","aashirvaad","amul","colgate","nivea","lakme","dove","maggi",
    "surf","clinic","parachute"
]

CATEGORY_CANONICAL = {
    "smartphone": "Smartphone",
    "laptop": "Laptop",
    "television": "Television",
    "fashion": "Fashion",
    "furniture": "Furniture",
    "kitchen": "Kitchen",
    "home appliance": "Home Appliance",
    "grocery": "Grocery",
    "beauty": "Beauty",
}

CATEGORY_SYNONYMS = {
    "smartphone": ["phone","mobile","smartphone"],
    "laptop": ["laptop","notebook"],
    "television": ["tv","television","smart tv"],
    "fashion": ["clothes","cloths","dress","shirt","tshirt","t-shirt","jeans",
                "hoodie","jacket","coat","kurti","kurta","shoes","sneaker",
                "fashion","wear","top"],
    "furniture": ["furniture","sofa","bed","almirah","wardrobe","chair",
                  "table","bookshelf","mattress"],
    "kitchen": ["kitchen","cooker","pressure cooker","stove","gas stove",
                "pan","fry pan","bottle","utensil"],
    "home appliance": ["appliance","fridge","refrigerator","washing machine",
                       "fan","bulb","chimney","heater","cooler","air cooler",
                       "purifier"],
    "grocery": ["grocery","atta","tea","noodles","maggi","detergent","butter","rice"],
    "beauty": ["beauty","cream","lotion","shampoo","kajal","serum","perfume",
               "lipstick","oil","cosmetic"],
}

# ---------- HELPER FUNCTIONS ----------

def product_image_url(name: str):
    """
    Simple placeholder image using product name as text.
    Doesn't require adding image URLs in CSV.
    """
    txt = quote_plus(name[:30])
    return f"https://via.placeholder.com/300x200.png?text={txt}"

def detect_brand(msg: str):
    for b in BRANDS:
        if b in msg:
            return b
    return None

def detect_category(msg: str):
    for logical_cat, words in CATEGORY_SYNONYMS.items():
        for w in words:
            if w in msg:
                return CATEGORY_CANONICAL[logical_cat]
    for logical_cat, canonical in CATEGORY_CANONICAL.items():
        if logical_cat in msg:
            return canonical
    return None

def detect_price_limit(msg: str):
    nums = re.findall(r"\d+", msg)
    if not nums:
        return None
    price = int(nums[0])
    if any(x in msg for x in ["under","below","less","<=","<","upto","up to","₹","rs","rs."]):
        return price
    return None

def filter_products(brand=None, category=None, price_limit=None):
    results = df.copy()
    if brand:
        results = results[results["name_lower"].str.contains(brand)]
    if category:
        results = results[results["category"].str.lower() == category.lower()]
    if price_limit is not None:
        results = results[results["price"] <= price_limit]
    return results.sort_values(["rating","price"], ascending=[False, True])

def find_similar(product_query: str):
    cand = df[df["name_lower"].str.contains(product_query)]
    if cand.empty:
        return None, None
    base = cand.iloc[0]
    cat = base["category"]
    price = base["price"]
    low = int(price * 0.7)
    high = int(price * 1.3)
    similar = df[
        (df["category"] == cat) &
        (df["price"] >= low) &
        (df["price"] <= high) &
        (df["product_id"] != base["product_id"])
    ].sort_values(["rating","price"], ascending=[False, True])
    return base, similar

def help_text():
    return (
        "📘 *Help – Example queries:*\n"
        "- `samsung phone under 30000`\n"
        "- `best laptop`\n"
        "- `recommend tv`\n"
        "- `nike shoes`\n"
        "- `similar to iPhone 15`\n"
        "- `beauty products under 500`\n"
        "- `grocery items`"
    )

def get_deal_of_the_day():
    """Pick a 'deal of the day' product: high rating + low price."""
    candidates = df[df["rating"] >= 4.5].sort_values(["price"], ascending=[True])
    if candidates.empty:
        candidates = df.sort_values(["rating","price"], ascending=[False, True])
    # random pick from top 10 candidates
    top_n = candidates.head(10)
    row = top_n.sample(1).iloc[0]
    return row

# ---------- MAIN CHATBOT LOGIC WITH PERSONALITY ----------

def chatbot_logic(msg: str, history: list):
    msg_low = msg.lower().strip()
    user_name = st.session_state.get("user") or ""
    # personalized calling name
    if user_name:
        nice_name = f"{user_name} bhai"
    else:
        nice_name = "bhai"

    # HELP
    if msg_low in ["help","menu","commands"]:
        return help_text(), None

    # GREETING
    if any(g in msg_low for g in ["hello","hi "," hi","hey","namaste","yo","sup","hii","hlo"]):
        deal = get_deal_of_the_day()
        return (
            f"Hello {nice_name} 👋\n"
            "Main aapka smart shopping assistant hoon.\n\n"
            "Aap mujhe aise bol sakte ho:\n"
            "- `samsung phone under 25000`\n"
            "- `best laptop`\n"
            "- `nike shoes`\n"
            "- `similar to iPhone 15`\n\n"
            f"⭐ Aaj ka special deal:\n"
            f"**{deal['product_name']}** (₹{deal['price']}, ⭐ {deal['rating']}) – "
            "ye price ke hisaab se kaafi strong option lag raha hai. 🔥"
        ), None

    # SIMILAR PRODUCTS
    if "similar to" in msg_low or msg_low.startswith("similar "):
        cleaned = (
            msg_low.replace("similar to","")
                   .replace("similar","")
                   .replace("products","")
                   .replace("show","")
                   .strip()
        )
        if not cleaned:
            return f"Kis product ke similar chahiye {nice_name}? Example: `similar to iPhone 15`", None
        base, sim = find_similar(cleaned)
        if base is None:
            return f"❌ `{cleaned}` jaise koi product nahi mila {nice_name}. Naam thoda clear likh ke try karo.", None
        if sim is None or sim.empty:
            return f"'{base['product_name']}' ke price/range me koi aur similar option nahi mila 😅", None
        
        text = (
            f"🔁 {nice_name}, aapne **similar products** puchha: **{base['product_name']}**\n\n"
            f"Ye saare options bhi **{base['category']}** hai, "
            f"aur lagbhag usi price range (±30%) me hai. Inme se aap kuch dekh sakte ho 👇"
        )
        return text, sim

    # PARSE FILTERS
    wants_reco = any(x in msg_low for x in ["best","recommend","suggest","top"])

    brand = detect_brand(msg_low)
    category = detect_category(msg_low)
    price_limit = detect_price_limit(msg_low)

    history.append({"user": msg, "brand": brand, "category": category, "price_limit": price_limit})
    if len(history) > 30:
        history.pop(0)

    # try to infer from previous history if needed later
    last_cat = None
    last_brand = None
    for h in reversed(history):
        if not last_cat and h.get("category"):
            last_cat = h["category"]
        if not last_brand and h.get("brand"):
            last_brand = h["brand"]
        if last_cat and last_brand:
            break

    # BRAND/CATEGORY/PRICE FILTER
    if brand or category or price_limit is not None:
        results = filter_products(brand=brand, category=category, price_limit=price_limit)

        if not results.empty:
            top = results.iloc[0]
            bullet_intro = []

            if brand:
                bullet_intro.append(f"brand **{brand.title()}**")
            if category:
                bullet_intro.append(f"category **{category}**")
            if price_limit is not None:
                bullet_intro.append(f"budget **₹{price_limit} tak**")

            criteria_text = ", ".join(bullet_intro) if bullet_intro else "aapke criteria ke hisaab se"

            deal = get_deal_of_the_day()

            text = (
                f"✅ {nice_name}, {criteria_text} jo sabse sahi lag raha hai wo hai:\n\n"
                f"**{top['product_name']}** (₹{top['price']}, ⭐ {top['rating']})\n"
                f"- Category: {top['category']}\n"
                f"- Reason: Rating achhi hai aur price aapke range me fit ho raha hai.\n\n"
                f"Neeche maine aur options bhi list kiye hain jo aap compare kar sakte ho 👇\n\n"
                f"💥 Aaj ka special deal (overall): **{deal['product_name']}** "
                f"(₹{deal['price']}, ⭐ {deal['rating']}) – "
                "agar extra option soch rahe ho to isko bhi check kar sakte ho."
            )
            return text, results

        # fallback -> best overall
        best = df.sort_values(["rating","price"], ascending=[False,True]).head(10)
        deal = get_deal_of_the_day()
        text = (
            f"❌ {nice_name}, aapke exact filter se koi product nahi mila.\n\n"
            "Par tension nahi 😄, rating ke hisaab se ye top products hai:\n\n"
            f"💥 Aaj ka special deal: **{deal['product_name']}** "
            f"(₹{deal['price']}, ⭐ {deal['rating']})\n"
            "Baaki options niche list kiye hain 👇"
        )
        return text, best

    # ONLY "BEST" / "RECOMMEND"
    if wants_reco:
        # 1st priority: current message se category detect
        cat_guess = detect_category(msg_low)

        # 2nd: previous history se guess
        if not cat_guess and last_cat:
            cat_guess = last_cat

        if cat_guess:
            best_cat = filter_products(category=cat_guess)
            top = best_cat.iloc[0]
            deal = get_deal_of_the_day()
            text = (
                f"⭐ {nice_name}, aapke recent interest ko dekh kar "
                f"**{cat_guess}** me yeh best option lag raha hai:\n\n"
                f"**{top['product_name']}** (₹{top['price']}, ⭐ {top['rating']})\n"
                f"- Category: {top['category']}\n\n"
                "Aur same category ke kuch aur ache options niche diye hain 👇\n\n"
                f"💥 Aaj ka special deal (global): **{deal['product_name']}** "
                f"(₹{deal['price']}, ⭐ {deal['rating']})"
            )
            return text, best_cat

        # fallback: overall best using previous brand also
        best = df.sort_values(["rating","price"], ascending=[False,True]).head(10)
        top = best.iloc[0]
        deal = get_deal_of_the_day()
        brand_hint = f" (aap pehle zyada **{last_brand}** dekh rahe the)" if last_brand else ""
        text = (
            f"⭐ {nice_name}, overall jo product sabse strong lag raha hai{brand_hint}:\n\n"
            f"**{top['product_name']}** (₹{top['price']}, ⭐ {top['rating']})\n\n"
            "Baaki aur top rated options niche diye hain 👇\n\n"
            f"💥 Aaj ka special deal: **{deal['product_name']}** "
            f"(₹{deal['price']}, ⭐ {deal['rating']})"
        )
        return text, best

    # DIRECT NAME SEARCH
    direct = df[df["name_lower"].str.contains(msg_low)]
    if not direct.empty:
        top = direct.iloc[0]
        deal = get_deal_of_the_day()
        text = (
            f"🔍 {nice_name}, aapne naam se search kiya hai.\n"
            f"Mujhe yeh product mila:\n\n"
            f"**{top['product_name']}** (₹{top['price']}, ⭐ {top['rating']})\n\n"
            "Same naam/range ke kuch aur items bhi niche diye hai 👇\n\n"
            f"💥 Aaj ka ek aur deal jo aapko pasand aa sakta hai: **{deal['product_name']}** "
            f"(₹{deal['price']}, ⭐ {deal['rating']})"
        )
        return text, direct

    # FALLBACK
    return (
        f"❓ {nice_name}, exact samajh nahi aaya aap kya chahte ho 😅\n\n"
        "Aise try karo:\n"
        "- `samsung phone under 25000`\n"
        "- `best laptop`\n"
        "- `nike shoes`\n"
        "- `tv under 50000`\n"
        "- `similar to iPhone 15`\n"
        "- `help`\n\n"
        "Phir main aapke liye smart recommendation ke saath full list dunga 🙂"
    ), None

# ---------- STREAMLIT UI SETUP ----------

st.set_page_config(page_title="Product Chatbot", page_icon="🛒", layout="wide")

# Session init
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []
if "cart" not in st.session_state:
    st.session_state.cart = []    # list of product_ids
if "user" not in st.session_state:
    st.session_state.user = ""
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "recommendation_count" not in st.session_state:
    st.session_state.recommendation_count = 0  # jitni baar results diye

# ---------- LOGIN SCREEN ----------
if not st.session_state.logged_in:
    st.title("🔐 Product Chatbot Login")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if username in USERS and USERS[username] == password:
                st.session_state.logged_in = True
                st.session_state.user = username
                st.success(f"Login successful! Welcome, {username} 👋")
            else:
                st.error("❌ Invalid username or password")

    st.stop()  # Do not show rest of app until logged in

# ---------- SIDEBAR: USER + CART + VOICE + COUNTER ----------

with st.sidebar:
    st.header("👤 User")
    st.write(f"Logged in as: **{st.session_state.user}**")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user = ""
        st.session_state.messages = []
        st.session_state.history = []
        st.session_state.cart = []
        st.session_state.recommendation_count = 0
        st.experimental_rerun()

    st.markdown("---")
    st.header("🛒 Cart")

    if st.session_state.cart:
        cart_df = df[df["product_id"].isin(st.session_state.cart)]
        total = int(cart_df["price"].sum())
        for _, r in cart_df.iterrows():
            st.write(f"- {r['product_name']} (₹{r['price']})")
        st.write(f"**Total: ₹{total}**")
        if st.button("🧹 Clear Cart"):
            st.session_state.cart = []
    else:
        st.write("Cart is empty.")

    st.markdown("---")
    st.header("📊 Stats")
    st.write(f"Total Recommendations Served: **{st.session_state.recommendation_count}**")

    st.markdown("---")
    st.header("🎙 Voice Command (Optional)")
    st.caption("Upload voice, we convert to text. Phir upar chat box me use kar sakte ho.")

    audio_file = st.file_uploader("Upload voice (wav/mp3)", type=["wav","mp3"], key="voice_uploader")
    if audio_file is not None:
        try:
            audio_bytes = audio_file.read()
            sound = AudioSegment.from_file(BytesIO(audio_bytes))
            wav_io = BytesIO()
            sound.export(wav_io, format="wav")
            wav_io.seek(0)

            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="en-IN")
            st.success("Recognized text:")
            st.code(text)
            st.info("Is text ko upar chat me paste karke send kar sakte ho. 🙂")
        except Exception as e:
            st.error(f"Voice processing error: {e}")

    st.markdown("---")
    st.caption("Tip: Try `samsung phone under 20000` or `similar to iPhone 15`")

# ---------- MAIN UI ----------

st.title("🛒 Product Recommendation Chatbot")
st.caption("Personal shopping assistant – brand + price + category + similar items + cart + voice + login")

# Show chat history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Chat input
user_msg = st.chat_input("Type your query (e.g. 'samsung phone under 25000')")

results_df = None
reply_text = None

if user_msg:
    st.session_state.messages.append({"role": "user", "content": user_msg})
    with st.chat_message("user"):
        st.markdown(user_msg)

    reply_text, results_df = chatbot_logic(user_msg, st.session_state.history)

    if results_df is not None and not results_df.empty:
        st.session_state.recommendation_count += 1

    st.session_state.messages.append({"role": "assistant", "content": reply_text})
    with st.chat_message("assistant"):
        st.markdown(reply_text)

    if results_df is not None and not results_df.empty:
        st.subheader("Results")
        cols = st.columns(2)
        for idx, (_, row) in enumerate(results_df.head(10).iterrows()):
            col = cols[idx % 2]
            with col:
                st.markdown(f"**{row['product_name']}**")
                st.write(f"Category: {row['category']}")
                st.write(f"Price: ₹{row['price']}")
                st.write(f"Rating: ⭐ {row['rating']}")
                img_url = product_image_url(row["product_name"])
                st.image(img_url, use_container_width=True)
                if st.button("➕ Add to Cart", key=f"add_{row['product_id']}_{idx}"):
                    if row["product_id"] not in st.session_state.cart:
                        st.session_state.cart.append(row["product_id"])
                        st.toast(f"Added to cart: {row['product_name']}")
                    else:
                        st.toast("Already in cart")

st.markdown("---")
st.markdown("👨‍💻 Built with Python + Streamlit + your custom dataset.")
