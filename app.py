import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
from datetime import datetime

# ============================================================
# CRUSH-IT FRAMEWORK ENGINE
# ============================================================

def is_crush_it_soccer(ml, spread, total, home_form=None, opp_defense=None, early_scorer=None):
    score = 0
    reasons = []

    if ml is not None and ml <= -500 and ml >= -1200:
        score += 3
        reasons.append(f"Heavy favorite ({ml})")
    elif ml is not None and ml < -300:
        score += 1
        reasons.append(f"Strong favorite ({ml})")

    if spread is not None and spread <= -2.5:
        score += 2
        reasons.append(f"Big spread ({spread})")
    elif spread is not None and spread <= -1.5:
        score += 1
        reasons.append(f"Decent spread ({spread})")

    if total is not None and total >= 3.5:
        score += 2
        reasons.append(f"High total ({total})")
    elif total is not None and total >= 3.0:
        score += 1
        reasons.append(f"Solid total ({total})")

    if home_form == "Elite":
        score += 2
        reasons.append("Elite home form")
    if opp_defense == "Bottom-tier":
        score += 2
        reasons.append("Weak opponent defense")
    if early_scorer:
        score += 1
        reasons.append("Early scoring profile")

    is_crush = score >= 5
    return is_crush, score, reasons


def classify_bet_type(market):
    market = market.lower()
    safe = ["ml", "moneyline", "fh ml", "first half ml", "team to score 2+", "team total 2+"]
    tempo = ["win both halves", "ml + over", "spread", "-1.5", "-2.5", "both halves"]
    
    for s in safe:
        if s in market:
            return "Safe Anchor"
    for t in tempo:
        if t in market:
            return "Tempo-Domination"
    return "Other"


def build_parlay_suggestions(candidates):
    early = [c for c in candidates if c.get("layer") == "Early"]
    late = [c for c in candidates if c.get("layer") == "Late"]

    suggestions = []

    if early and late:
        for e in early[:2]:
            for l in late[:2]:
                if l.get("is_crush"):
                    suggestions.append({
                        "tier": "Tier 1 - Safe",
                        "legs": [e, l],
                        "risk": "Low",
                        "note": "Anchor + early safe leg"
                    })

    if late:
        crush_late = [l for l in late if l.get("is_crush")]
        tempo_late = [l for l in late if l.get("bet_type") == "Tempo-Domination"]
        for c in crush_late[:2]:
            for t in tempo_late[:2]:
                if c["team"] != t["team"]:
                    suggestions.append({
                        "tier": "Tier 2 - Balanced",
                        "legs": [c, t],
                        "risk": "Medium",
                        "note": "Crush anchor + tempo leg"
                    })

    tempo_legs = [c for c in candidates if c.get("bet_type") == "Tempo-Domination"]
    if len(tempo_legs) >= 2:
        suggestions.append({
            "tier": "Tier 3 - Aggressive",
            "legs": tempo_legs[:2],
            "risk": "High",
            "note": "Two tempo-domination legs"
        })

    return suggestions[:6]


def trap_check(team, notes=""):
    traps = ["slow tempo", "counter attack", "road favorite", "rotation", "heavy rotation",
             "inconsistent", "low total", "paper favorite"]
    notes_lower = notes.lower()
    for t in traps:
        if t in notes_lower:
            return True, t
    return False, None


# ============================================================
# STREAMLIT UI
# ============================================================

st.set_page_config(
    page_title="Crush-It Betmaker",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚽ Crush-It Betmaker")
st.caption("Soccer • Tennis • UFC | Framework by you + Grok engine")

with st.sidebar:
    st.header("Settings")
    sport = st.selectbox("Sport", ["Soccer", "Tennis", "UFC"])
    bankroll = st.number_input("Bankroll ($)", min_value=50, value=500, step=50)
    risk_pct = st.slider("Max risk per parlay %", 1, 10, 3)
    st.markdown("---")
    st.info("Upload screenshots of Sportsbook RI or enter lines manually.")

tab1, tab2, tab3, tab4 = st.tabs(["📥 Input Lines", "🔥 Crush-It Scanner", "🎯 Parlay Builder", "📋 System Rules"])

with tab1:
    st.subheader("Add Matches / Lines")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### Screenshot Upload")
        uploaded = st.file_uploader("Upload Sportsbook RI screenshot", type=["png", "jpg", "jpeg"])
        if uploaded:
            image = Image.open(uploaded)
            st.image(image, caption="Uploaded board", use_container_width=True)

            if st.button("Run OCR (experimental)"):
                with st.spinner("Extracting text..."):
                    text = pytesseract.image_to_string(image)
                    st.text_area("Raw OCR output", text, height=200)

    with col2:
        st.markdown("#### Manual Entry")
        with st.form("add_match"):
            team = st.text_input("Team / Fighter (favorite side)")
            opponent = st.text_input("Opponent")
            ml = st.number_input("Moneyline (American, e.g. -650)", value=-650, step=10)
            spread = st.number_input("Spread (e.g. -2.5)", value=-2.5, step=0.5)
            total = st.number_input("Total (e.g. 3.5)", value=3.5, step=0.25)
            market = st.selectbox("Primary Market", [
                "ML", "FH ML", "Team to score 2+", "Win Both Halves",
                "ML + Over", "Spread -1.5", "Spread -2.5", "Other"
            ])
            layer = st.radio("Layer", ["Early", "Late"], horizontal=True)
            home_form = st.selectbox("Home Form", ["Unknown", "Elite", "Good", "Average"])
            opp_def = st.selectbox("Opp Defense", ["Unknown", "Bottom-tier", "Average", "Strong"])
            early_scorer = st.checkbox("Early scoring profile?")
            notes = st.text_area("Notes / Trap flags")
            submitted = st.form_submit_button("Add to Board")

            if submitted and team:
                if "board" not in st.session_state:
                    st.session_state.board = []

                is_crush, score, reasons = is_crush_it_soccer(
                    ml, spread, total, home_form, opp_def, early_scorer
                )
                is_trap, trap_reason = trap_check(team, notes)

                entry = {
                    "team": team,
                    "opponent": opponent,
                    "ml": ml,
                    "spread": spread,
                    "total": total,
                    "market": market,
                    "layer": layer,
                    "home_form": home_form,
                    "opp_def": opp_def,
                    "early_scorer": early_scorer,
                    "notes": notes,
                    "is_crush": is_crush and not is_trap,
                    "score": score,
                    "reasons": reasons,
                    "is_trap": is_trap,
                    "trap_reason": trap_reason,
                    "bet_type": classify_bet_type(market),
                    "timestamp": datetime.now().strftime("%H:%M")
                }
                st.session_state.board.append(entry)
                st.success(f"Added {team} | Crush-It: {'YES' if entry['is_crush'] else 'No'} (score {score})")

with tab2:
    st.subheader("Crush-It Scanner")

    if "board" not in st.session_state or len(st.session_state.board) == 0:
        st.warning("No matches added yet. Go to Input Lines tab.")
    else:
        df = pd.DataFrame(st.session_state.board)

        show_only_crush = st.checkbox("Show only Crush-It flags", value=False)
        if show_only_crush:
            df = df[df["is_crush"] == True]

        for idx, row in df.iterrows():
            color = "🟢" if row["is_crush"] else ("🔴" if row["is_trap"] else "⚪")
            with st.expander(f"{color} {row['team']} vs {row['opponent']} | {row['market']} | Score: {row['score']}"):
                c1, c2, c3 = st.columns(3)
                c1.metric("ML", row["ml"])
                c2.metric("Spread", row["spread"])
                c3.metric("Total", row["total"])
                st.write(f"**Layer:** {row['layer']} | **Type:** {row['bet_type']}")
                if row["reasons"]:
                    st.write("**Reasons:** " + " • ".join(row["reasons"]))
                if row["is_trap"]:
                    st.error(f"TRAP FLAG: {row['trap_reason']}")
                if row["notes"]:
                    st.write(f"Notes: {row['notes']}")

        if st.button("Clear Board"):
            st.session_state.board = []
            st.rerun()

with tab3:
    st.subheader("Parlay Builder (3-Tier System)")

    if "board" not in st.session_state or len(st.session_state.board) < 2:
        st.info("Need at least 2 legs on the board.")
    else:
        candidates = st.session_state.board
        suggestions = build_parlay_suggestions(candidates)

        if not suggestions:
            st.warning("Not enough qualifying legs for auto-suggestions.")
        else:
            for s in suggestions:
                st.markdown(f"### {s['tier']}  ({s['risk']})")
                st.caption(s["note"])
                legs_text = []
                for leg in s["legs"]:
                    legs_text.append(f"{leg['team']} {leg['market']} ({leg['ml']})")
                st.code(" + ".join(legs_text))
                st.markdown("---")

        st.markdown("#### Manual Parlay Builder")
        selected = st.multiselect(
            "Pick legs",
            options=[f"{b['team']} | {b['market']} | {b['ml']}" for b in candidates]
        )
        if selected and len(selected) >= 2:
            st.success(f"Selected {len(selected)}-leg parlay")
            st.write(selected)
            stake = bankroll * (risk_pct / 100)
            st.metric("Suggested stake", f"${stake:.0f}")

with tab4:
    st.subheader("Crush-It Framework (Your Rules)")

    st.markdown("""
### 1. Identify True Crush-It Teams
- Heavy favorite (-500 to -1200)
- Spread -2.5 or higher
- Total goals 3.5 or higher
- Elite home form
- Opponent with bottom-tier defense
- Early-scoring profile

### 2. Two Bet Types
**Safe Anchor**: ML, FH ML, Team to score 2+  
**Tempo-Domination**: Win both halves, ML + Over, Spread -1.5/-2.5

### 3. Parlay Structure
Layer 1 – Early | Layer 2 – Late Crush-It  
Tier 1 Safe | Tier 2 Balanced | Tier 3 Aggressive

### 4. Live Adjustments
When Crush-It scores early → Over 3.5 / -2.5 / Team total 2.5

### 5. Trap Avoidance
Avoid slow-tempo, counter-attack, inconsistent road favorites, heavy rotation, low totals.
""")

st.markdown("---")
st.caption(f"Crush-It Betmaker v1 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
