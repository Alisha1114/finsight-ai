import streamlit as st
import plotly.graph_objects as go
from groq import Groq
import json

st.set_page_config(page_title="FinSight AI", page_icon="💰", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0a0f;
    color: #e8e8f0;
}
h1, h2, h3, h4 { font-family: 'Syne', sans-serif; }
.stApp { background: linear-gradient(135deg, #0a0a0f, #0f0f1a, #0a0a0f); }

.score-card {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border: 1px solid #00f5a0;
    border-radius: 20px;
    padding: 2rem;
    text-align: center;
    box-shadow: 0 0 40px rgba(0,245,160,0.15);
}
.score-number {
    font-family: 'Syne', sans-serif;
    font-size: 5rem;
    font-weight: 800;
    line-height: 1;
}
.score-label {
    font-size: 0.85rem;
    color: #888;
    margin-top: 0.5rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
}
.card {
    background: #13131f;
    border: 1px solid #1e1e35;
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    margin: 0.5rem 0;
}
.card:hover { border-color: #00f5a040; }
.card-title { font-size: 0.72rem; color: #555; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 0.3rem; }
.card-value { font-family: 'Syne', sans-serif; font-size: 1.6rem; font-weight: 700; }
.card-sub { font-size: 0.78rem; color: #444; margin-top: 0.2rem; }

.risk-item {
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin: 0.35rem 0;
    font-size: 0.88rem;
}
.risk-high { background: rgba(245,64,64,0.08); border-left: 3px solid #f54040; }
.risk-medium { background: rgba(245,196,0,0.08); border-left: 3px solid #f5c400; }
.risk-low { background: rgba(0,245,160,0.08); border-left: 3px solid #00f5a0; }

.action-card {
    background: #13131f;
    border: 1px solid #1e1e35;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
}
.chat-user {
    background: #1a1a35;
    border-left: 3px solid #00f5a0;
    border-radius: 0 10px 10px 0;
    padding: 0.7rem 1rem;
    margin: 0.4rem 0;
    font-size: 0.9rem;
}
.chat-ai {
    background: #13131f;
    border-left: 3px solid #00d9f5;
    border-radius: 0 10px 10px 0;
    padding: 0.7rem 1rem;
    margin: 0.4rem 0;
    font-size: 0.9rem;
}
[data-testid="stSidebar"] { background: #0d0d18 !important; border-right: 1px solid #1a1a30; }
.stButton > button {
    background: linear-gradient(135deg, #00f5a0, #00d9f5);
    color: #0a0a0f;
    border: none;
    border-radius: 10px;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    width: 100%;
}
.stButton > button:hover { opacity: 0.85; }
.stNumberInput input, .stTextInput input {
    background: #13131f !important;
    border: 1px solid #1e1e35 !important;
    color: #e8e8f0 !important;
    border-radius: 8px !important;
}
hr { border-color: #1a1a30; }
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def get_client(api_key):
    return Groq(api_key=api_key)

def score_color(score):
    if score >= 75: return "#00f5a0"
    if score >= 50: return "#f5c400"
    return "#f54040"

def score_label(score):
    if score >= 75: return "Excellent"
    if score >= 50: return "Needs Work"
    return "Critical"

def compute_score(income, expenses, savings, debt, investments):
    score = 50
    if income > 0:
        if savings / income >= 0.20: score += 20
        elif savings / income >= 0.10: score += 10
        elif savings / income < 0: score -= 15

        if expenses / income <= 0.50: score += 15
        elif expenses / income <= 0.70: score += 5
        elif expenses / income > 0.90: score -= 15

    if debt == 0:
        score += 10
    elif income > 0 and debt / (income * 12) < 0.36:
        score += 5
    elif income > 0 and debt / (income * 12) > 1.0:
        score -= 15

    if investments > 0:
        score += 5

    return max(0, min(100, score))

def detect_risks(income, expenses, savings, debt, investments):
    risks = []
    if income > 0:
        if expenses / income > 0.90:
            risks.append({"level": "high", "text": "Expenses are over 90% of income — one emergency could wipe you out"})
        elif expenses / income > 0.75:
            risks.append({"level": "medium", "text": "Expenses are high relative to income — limited room to save"})

        if savings / income < 0.05:
            risks.append({"level": "high", "text": "Savings rate is below 5% — you have almost no financial buffer"})

        if debt > 0 and debt / (income * 12) > 0.5:
            risks.append({"level": "high", "text": f"Debt is {debt/(income*12)*100:.0f}% of your annual income — this is a serious risk"})
        elif debt > 0 and debt / (income * 12) > 0.36:
            risks.append({"level": "medium", "text": "Debt-to-income ratio is above the safe threshold of 36%"})

    if savings < expenses * 3:
        risks.append({"level": "medium", "text": "Emergency fund is below 3 months of expenses — build this up first"})

    if investments == 0:
        risks.append({"level": "low", "text": "No investments detected — your money is not growing over time"})

    if not risks:
        risks.append({"level": "low", "text": "No major financial risks detected — you are on the right track!"})

    return risks

def project_wealth(income, expenses, savings, debt, investments, years=20):
    years_list = list(range(0, years + 1))
    net_worth_values = []
    current_investments = investments
    current_debt = debt

    for y in years_list:
        net_worth = current_investments - current_debt
        net_worth_values.append(round(net_worth))
        current_investments = current_investments * 1.07 + (savings * 12)
        current_debt = max(0, current_debt - (savings * 12 * 0.3))

    return years_list, net_worth_values


# ── AI functions ──────────────────────────────────────────────────────────────

def get_ai_analysis(client, income, expenses, savings, debt, investments, score):
    prompt = f"""You are FinSight AI, a personal finance advisor. Analyze this situation.

Data:
- Monthly Income: ${income}
- Monthly Expenses: ${expenses}
- Monthly Savings: ${savings}
- Total Debt: ${debt}
- Total Investments: ${investments}
- Financial Health Score: {score}/100

Reply ONLY with this JSON, no extra text, no markdown backticks:
{{
  "summary": "2-3 sentence plain English assessment",
  "strengths": ["strength 1", "strength 2"],
  "warnings": ["warning 1", "warning 2"],
  "actions": [
    {{"title": "short title", "detail": "specific step", "impact": "high"}},
    {{"title": "short title", "detail": "specific step", "impact": "medium"}},
    {{"title": "short title", "detail": "specific step", "impact": "low"}}
  ],
  "debt_plan": "plain text debt strategy, or null if no debt",
  "savings_target": "$X per month"
}}"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=900
    )
    raw = res.choices[0].message.content.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def chat_with_advisor(client, user_msg, context, history):
    system = f"""You are FinSight AI, a friendly personal finance advisor.
User profile: {context}
Be direct and helpful. Keep answers to 3-4 sentences max."""

    messages = [{"role": "system", "content": system}]
    for msg in history[-8:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_msg})

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.5,
        max_tokens=400
    )
    return res.choices[0].message.content


# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 💰 FinSight AI")
    st.markdown("*Personal Financial Health Agent*")
    st.markdown("---")

    api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    st.markdown("---")

    st.markdown("### Your Finances")
    income      = st.number_input("Monthly Income ($)",    min_value=0, value=4000, step=100)
    expenses    = st.number_input("Monthly Expenses ($)",  min_value=0, value=2800, step=100)
    savings     = st.number_input("Monthly Savings ($)",   min_value=0, value=400,  step=50)
    debt        = st.number_input("Total Debt ($)",        min_value=0, value=12000, step=500)
    investments = st.number_input("Total Investments ($)", min_value=0, value=3000,  step=500)

    st.markdown("### Expense Breakdown")
    housing   = st.number_input("Housing ($)",   min_value=0, value=1200, step=50)
    food      = st.number_input("Food ($)",      min_value=0, value=400,  step=50)
    transport = st.number_input("Transport ($)", min_value=0, value=300,  step=50)
    utilities = st.number_input("Utilities ($)", min_value=0, value=150,  step=25)
    other     = st.number_input("Other ($)",     min_value=0, value=750,  step=50)

    analyze_btn = st.button("🚀 Analyze My Finances")


# ── main ──────────────────────────────────────────────────────────────────────

st.markdown("# FinSight AI")
st.markdown("##### AI-Powered Personal Financial Health Agent")
st.markdown("---")

if not api_key:
    st.info("👈 Enter your Groq API key in the sidebar to get started.")
    st.stop()

client = get_client(api_key)

if "analysis" not in st.session_state: st.session_state.analysis = None
if "score"    not in st.session_state: st.session_state.score    = None
if "chat"     not in st.session_state: st.session_state.chat     = []
if "fin_ctx"  not in st.session_state: st.session_state.fin_ctx  = ""

if analyze_btn:
    score = compute_score(income, expenses, savings, debt, investments)
    st.session_state.score = score
    with st.spinner("Analyzing your finances..."):
        try:
            analysis = get_ai_analysis(client, income, expenses, savings, debt, investments, score)
            st.session_state.analysis = analysis
            st.session_state.fin_ctx = (
                f"Monthly income ${income}, expenses ${expenses}, savings ${savings}, "
                f"debt ${debt}, investments ${investments}, score {score}/100"
            )
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()


# ── dashboard ─────────────────────────────────────────────────────────────────

if st.session_state.analysis:
    analysis = st.session_state.analysis
    score    = st.session_state.score
    color    = score_color(score)
    label    = score_label(score)

    # score + metrics row
    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])

    with c1:
        st.markdown(f"""
        <div class="score-card">
            <div class="score-number" style="color:{color}">{score}</div>
            <div class="score-label">Financial Health Score</div>
            <div style="margin-top:0.5rem; color:{color}; font-weight:600; font-size:1rem">{label}</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        surplus = income - expenses
        sc = "#00f5a0" if surplus >= 0 else "#f54040"
        sr = (savings / income * 100) if income > 0 else 0
        src = "#00f5a0" if sr >= 20 else ("#f5c400" if sr >= 10 else "#f54040")
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Monthly Surplus</div>
            <div class="card-value" style="color:{sc}">${surplus:+,.0f}</div>
            <div class="card-sub">Income minus expenses</div>
        </div>
        <div class="card">
            <div class="card-title">Savings Rate</div>
            <div class="card-value" style="color:{src}">{sr:.1f}%</div>
            <div class="card-sub">Target: 20%+</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        dti = (debt / (income * 12) * 100) if income > 0 else 0
        dc = "#00f5a0" if dti < 36 else ("#f5c400" if dti < 50 else "#f54040")
        er = (expenses / income * 100) if income > 0 else 0
        ec = "#00f5a0" if er <= 70 else "#f54040"
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Debt-to-Income</div>
            <div class="card-value" style="color:{dc}">{dti:.0f}%</div>
            <div class="card-sub">Safe: under 36%</div>
        </div>
        <div class="card">
            <div class="card-title">Expense Ratio</div>
            <div class="card-value" style="color:{ec}">{er:.0f}%</div>
            <div class="card-sub">Of monthly income</div>
        </div>""", unsafe_allow_html=True)

    with c4:
        runway = (savings / expenses) if expenses > 0 else 0
        rc = "#00f5a0" if savings >= expenses * 3 else "#f54040"
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Investments</div>
            <div class="card-value">${investments:,.0f}</div>
            <div class="card-sub">Total portfolio</div>
        </div>
        <div class="card">
            <div class="card-title">Emergency Fund</div>
            <div class="card-value" style="color:{rc}">{runway:.1f}mo</div>
            <div class="card-sub">Target: 3–6 months</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", "🔮 Wealth Projector", "🎯 Budget Optimizer", "⚠️ Risk Detector", "💬 AI Advisor"
    ])

    # ── overview ──────────────────────────────────────────────────────────────
    with tab1:
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### Expense Breakdown")
            fig = go.Figure(go.Pie(
                labels=["Housing", "Food", "Transport", "Utilities", "Other"],
                values=[housing, food, transport, utilities, other],
                hole=0.55,
                marker=dict(
                    colors=["#00f5a0", "#00d9f5", "#a78bfa", "#f5c400", "#f54040"],
                    line=dict(color="#0a0a0f", width=2)
                ),
                textfont=dict(color="#e8e8f0", size=12)
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e8e8f0"),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#e8e8f0")),
                margin=dict(t=10, b=10, l=10, r=10), height=300
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown("#### Income Allocation")
            unallocated = max(0, income - expenses - savings)
            fig2 = go.Figure(go.Bar(
                x=["Expenses", "Savings", "Unallocated"],
                y=[expenses, savings, unallocated],
                marker=dict(color=["#f54040", "#00f5a0", "#2a2a4a"]),
                text=[f"${v:,.0f}" for v in [expenses, savings, unallocated]],
                textposition="outside",
                textfont=dict(color="#e8e8f0")
            ))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e8e8f0"),
                xaxis=dict(color="#e8e8f0", gridcolor="#1e1e35"),
                yaxis=dict(color="#e8e8f0", gridcolor="#1e1e35"),
                margin=dict(t=30, b=10, l=10, r=10), height=300
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        col_i, col_j = st.columns(2)

        with col_i:
            st.markdown("#### 🧠 AI Assessment")
            st.markdown(f"> {analysis.get('summary', '')}")
            st.markdown("**✅ Strengths**")
            for s in analysis.get("strengths", []):
                st.markdown(f"- {s}")
            st.markdown("**⚠️ Warnings**")
            for w in analysis.get("warnings", []):
                st.markdown(f"- {w}")
            debt_plan = analysis.get("debt_plan")
            if debt_plan and debt_plan != "null" and debt_plan is not None:
                st.markdown("**💳 Debt Strategy**")
                st.write(debt_plan)

        with col_j:
            st.markdown("#### ⚡ Action Plan")
            for i, action in enumerate(analysis.get("actions", []), 1):
                impact = action.get("impact", "medium")
                ic = "#00f5a0" if impact == "high" else ("#f5c400" if impact == "medium" else "#888")
                st.markdown(f"""
                <div class="action-card">
                    <div style="display:flex; justify-content:space-between">
                        <span style="font-size:0.7rem; color:#555; text-transform:uppercase">Action {i}</span>
                        <span style="font-size:0.7rem; color:{ic}; text-transform:uppercase">{impact} impact</span>
                    </div>
                    <div style="font-weight:600; margin:0.3rem 0">{action.get('title','')}</div>
                    <div style="font-size:0.84rem; color:#666">{action.get('detail','')}</div>
                </div>""", unsafe_allow_html=True)
            st.markdown(f"**🎯 Savings Target:** {analysis.get('savings_target', '')}")

    # ── wealth projector ──────────────────────────────────────────────────────
    with tab2:
        st.markdown("#### 🔮 Future Wealth Projector")
        st.markdown("See where you'll be financially if you keep your current habits — vs if you optimize.")

        years_list, current_nw = project_wealth(income, expenses, savings, debt, investments)
        _, optimized_nw = project_wealth(income, expenses, income * 0.20, debt, investments)

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=years_list, y=current_nw,
            name="Current Path",
            line=dict(color="#f5c400", width=2),
            fill="tozeroy", fillcolor="rgba(245,196,0,0.05)"
        ))
        fig3.add_trace(go.Scatter(
            x=years_list, y=optimized_nw,
            name="Optimized (20% savings)",
            line=dict(color="#00f5a0", width=2, dash="dash"),
            fill="tozeroy", fillcolor="rgba(0,245,160,0.05)"
        ))
        fig3.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e8e8f0"),
            xaxis=dict(title="Years from now", color="#e8e8f0", gridcolor="#1a1a30"),
            yaxis=dict(title="Net Worth ($)", color="#e8e8f0", gridcolor="#1a1a30"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#e8e8f0")),
            margin=dict(t=20, b=20, l=20, r=20), height=380
        )
        st.plotly_chart(fig3, use_container_width=True)

        p1, p2, p3 = st.columns(3)
        for col, yr in zip([p1, p2, p3], [5, 10, 20]):
            nw = current_nw[yr]
            c = "#00f5a0" if nw > 0 else "#f54040"
            with col:
                st.markdown(f"""
                <div class="card" style="text-align:center">
                    <div class="card-title">Net Worth in {yr} Years</div>
                    <div class="card-value" style="color:{c}">${nw:,.0f}</div>
                    <div class="card-sub">At current savings rate</div>
                </div>""", unsafe_allow_html=True)

        diff = optimized_nw[20] - current_nw[20]
        if diff > 0:
            st.info(f"💡 By saving 20% of your income, you could have **${diff:,.0f} more** in 20 years.")

    # ── budget optimizer ──────────────────────────────────────────────────────
    with tab3:
        st.markdown("#### 🎯 Budget Optimizer")
        st.markdown("Compare your spending to the recommended 50/30/20 rule.")

        needs = housing + food + transport + utilities
        col_b1, col_b2 = st.columns(2)

        with col_b1:
            st.markdown("**Your Current Budget**")
            current_items = {
                "Needs (Housing, Food, Bills)": needs,
                "Wants & Other": other,
                "Savings": savings,
            }
            for k, v in current_items.items():
                pct = (v / income * 100) if income > 0 else 0
                st.markdown(f"""
                <div class="card">
                    <div style="display:flex; justify-content:space-between; align-items:center">
                        <span style="font-weight:500">{k}</span>
                        <span style="font-family:'Syne',sans-serif; font-size:1.1rem">
                            ${v:,.0f} <span style="font-size:0.8rem; color:#555">({pct:.0f}%)</span>
                        </span>
                    </div>
                </div>""", unsafe_allow_html=True)

        with col_b2:
            st.markdown("**Recommended (50/30/20 Rule)**")
            suggested_items = {
                "Needs (50%)": round(income * 0.50),
                "Wants (30%)": round(income * 0.30),
                "Savings (20%)": round(income * 0.20),
            }
            for k, v in suggested_items.items():
                st.markdown(f"""
                <div class="card" style="border-color:#00f5a020">
                    <div style="display:flex; justify-content:space-between; align-items:center">
                        <span style="font-weight:500">{k}</span>
                        <span style="font-family:'Syne',sans-serif; font-size:1.1rem; color:#00f5a0">${v:,.0f}</span>
                    </div>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Visual Comparison**")
        fig4 = go.Figure()
        categories = ["Needs", "Wants", "Savings"]
        current_vals   = [needs, other, savings]
        suggested_vals = [round(income * 0.50), round(income * 0.30), round(income * 0.20)]

        fig4.add_trace(go.Bar(name="Your Budget",  x=categories, y=current_vals,  marker_color="#f5c400"))
        fig4.add_trace(go.Bar(name="Recommended",  x=categories, y=suggested_vals, marker_color="#00f5a0"))
        fig4.update_layout(
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e8e8f0"),
            xaxis=dict(color="#e8e8f0", gridcolor="#1a1a30"),
            yaxis=dict(color="#e8e8f0", gridcolor="#1a1a30"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#e8e8f0")),
            margin=dict(t=20, b=20, l=20, r=20), height=300
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ── risk detector ─────────────────────────────────────────────────────────
    with tab4:
        st.markdown("#### ⚠️ Financial Risk Detector")
        st.markdown("Automatic scan for financial danger patterns in your profile.")

        risks = detect_risks(income, expenses, savings, debt, investments)
        high_risks   = [r for r in risks if r["level"] == "high"]
        medium_risks = [r for r in risks if r["level"] == "medium"]
        low_risks    = [r for r in risks if r["level"] == "low"]

        r1, r2, r3 = st.columns(3)
        with r1:
            c = "#f54040" if high_risks else "#555"
            st.markdown(f"""
            <div class="card" style="text-align:center; border-color:{c}40">
                <div class="card-title">High Risk</div>
                <div class="card-value" style="color:{c}">{len(high_risks)}</div>
            </div>""", unsafe_allow_html=True)
        with r2:
            c = "#f5c400" if medium_risks else "#555"
            st.markdown(f"""
            <div class="card" style="text-align:center; border-color:{c}40">
                <div class="card-title">Medium Risk</div>
                <div class="card-value" style="color:{c}">{len(medium_risks)}</div>
            </div>""", unsafe_allow_html=True)
        with r3:
            c = "#00f5a0" if not high_risks and not medium_risks else "#555"
            st.markdown(f"""
            <div class="card" style="text-align:center; border-color:{c}40">
                <div class="card-title">Low Risk</div>
                <div class="card-value" style="color:{c}">{len(low_risks)}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Risk Breakdown**")
        for r in risks:
            icon = "🔴" if r["level"] == "high" else ("🟡" if r["level"] == "medium" else "🟢")
            st.markdown(
                f'<div class="risk-item risk-{r["level"]}">{icon} {r["text"]}</div>',
                unsafe_allow_html=True
            )

    # ── ai chat ───────────────────────────────────────────────────────────────
    with tab5:
        st.markdown("#### 💬 Ask Your AI Financial Advisor")
        st.markdown("Ask anything about your finances, budgeting, investing, or debt.")

        for msg in st.session_state.chat:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-user">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-ai">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

        col_inp, col_send = st.columns([5, 1])
        with col_inp:
            user_input = st.text_input(
                "Message", key="chat_input",
                label_visibility="collapsed",
                placeholder="e.g. How do I pay off my debt faster?"
            )
        with col_send:
            if st.button("Send"):
                if user_input.strip():
                    st.session_state.chat.append({"role": "user", "content": user_input})
                    with st.spinner("..."):
                        reply = chat_with_advisor(
                            client, user_input,
                            st.session_state.fin_ctx,
                            st.session_state.chat
                        )
                    st.session_state.chat.append({"role": "assistant", "content": reply})
                    st.rerun()

else:
    st.markdown("""
    <div style="text-align:center; padding:4rem 2rem">
        <div style="font-size:4rem">💰</div>
        <h2 style="font-family:'Syne',sans-serif; font-size:2rem; margin:1rem 0">
            Know Your Financial Health Score
        </h2>
        <p style="color:#555; max-width:500px; margin:0 auto">
            Enter your financial details in the sidebar and hit <strong>Analyze</strong> to get your 
            score, wealth projection, budget optimization, risk analysis, and AI advisor.
        </p>
    </div>
    """, unsafe_allow_html=True)
