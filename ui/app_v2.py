import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import your backend orchestrator
from backend.orchestrator.main_graph import run_query
from backend.utils.helper import escape_markdown, escape_dollar_signs

# ------------------------------------------------
# Suggestion Queries
# ------------------------------------------------
SUGGESTION_QUERIES = [
    "What stocks do I own?",
    "Show me my best performing holdings",
    "What's my portfolio allocation by sector?",
    "How is Tesla performing?",
    "Compare Apple and Microsoft",
    "What's the latest news on NVIDIA?",
]

# ------------------------------------------------
# 1. Header
# ------------------------------------------------
def header():
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.title("Portfolio & Market Intelligence Assistant")
    with col2:
        if "client_id" in st.session_state:
            st.info(f"Client: {st.session_state['client_id']}")
            if st.button("Reset Session", key="reset_session_btn"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

# ------------------------------------------------
# 2. Sidebar - Session
# ------------------------------------------------
def session_sidebar(client_ids):
    st.sidebar.subheader("Session")
    selected_client = st.sidebar.selectbox("Select Client ID", client_ids)
    if st.sidebar.button("Start Session", key="start_session_btn"):
        st.session_state["client_id"] = selected_client
        st.session_state["session_id"] = f"sess_{selected_client}"
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
    if "client_id" in st.session_state:
        st.sidebar.markdown(f"**Logged in as:** {st.session_state['client_id']}")
        if st.sidebar.button("Logout", key="logout_btn"):
            # Clear entire session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# ------------------------------------------------
# 3. Sidebar - Portfolio Overview Snapshot
# ------------------------------------------------
def portfolio_snapshot(portfolio_data):
    st.sidebar.subheader("Portfolio Overview")

    if not portfolio_data or portfolio_data.get("status") != "success":
        st.sidebar.write("No portfolio data loaded.")
        return

    results = portfolio_data.get("results", [])
    try:
        if results:
            df = pd.DataFrame(results)
            st.sidebar.dataframe(df)

        # sector allocation chart if available
        if "portfolio_summary" in portfolio_data:
            alloc = portfolio_data["portfolio_summary"].get("sector_allocations", {})
            if alloc:
                alloc_df = pd.DataFrame({"Sector": list(alloc.keys()), "Allocation": list(alloc.values())})
                fig = px.pie(alloc_df, names="Sector", values="Allocation")
                st.sidebar.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.sidebar.write("No portfolio data loaded.")
        
# ------------------------------------------------
# 4. Sidebar - Market Intelligence Snapshot
# ------------------------------------------------
def market_snapshot(market_data):
    st.sidebar.subheader("Market Intelligence")
    if not market_data or market_data.get("status") != "success":
        st.sidebar.write("No market data available.")
        return

    results = market_data.get("results", {})
    for ticker, info in results.items():
        st.sidebar.markdown(f"**{ticker}** — ${info.get('price', 'N/A')}")
        if info.get("news"):
            st.sidebar.caption(f"{info['news'][0]}")

# ------------------------------------------------
# 5. Optional Debug Panel
# ------------------------------------------------
def debug_panel(debug_data):
    if st.sidebar.checkbox("Enable Debug Mode", key="debug_mode_checkbox"):
        st.sidebar.subheader("Debug Info")
        st.sidebar.json(debug_data)

# ------------------------------------------------
# 6. Welcome Message
# ------------------------------------------------
def welcome_message():
    st.markdown("""
    ### 👋 Welcome to your Portfolio Intelligence Assistant!
    
    I can help you with:
    - 📊 **Portfolio Analysis**: View your holdings, returns, and allocations
    - 📈 **Market Intelligence**: Get latest news, prices, and filings
    - 🔍 **Impact Analysis**: Understand how market events affect your portfolio
    - 📉 **Performance Tracking**: Compare stocks and identify top performers
    
    **Get started by selecting a query below or typing your own question.**
    """)

# ------------------------------------------------
# 7. Suggestion Chips
# ------------------------------------------------
def suggestion_chips():
    st.markdown("##### 💡 Try asking:")
    
    # Create columns for suggestion chips (3 per row)
    cols = st.columns(3)
    
    for idx, suggestion in enumerate(SUGGESTION_QUERIES):
        col_idx = idx % 3
        with cols[col_idx]:
            if st.button(suggestion, key=f"suggestion_{idx}", use_container_width=True):
                # Set the suggestion as the query to process
                st.session_state["pending_query"] = suggestion
                st.rerun()

# ------------------------------------------------
# 8. Main Chat Interface
# ------------------------------------------------
def chat_interface():
    st.subheader("Assistant")
    
    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    
    # Show welcome message only if chat is empty
    if len(st.session_state["chat_history"]) == 0:
        welcome_message()
        suggestion_chips()
        st.markdown("---")
    
    # Display chat history
    chat_container = st.container()
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            chat_container.markdown(f"**You:** {msg['text']}")
        else:
            chat_container.markdown(f"**Assistant:** {msg['text']}")
    
    # Handle pending query from suggestion chips
    if "pending_query" in st.session_state:
        query = st.session_state["pending_query"]
        del st.session_state["pending_query"]
        process_query(query)
        st.rerun()
    
    # User input box - always empty after submission
    query = st.text_input(
        "Ask your question:", 
        key=f"user_query_{len(st.session_state['chat_history'])}", 
        placeholder="e.g. What are my holdings?"
    )
    
    if st.button("Submit", key="submit_query_btn") and query:
        process_query(query)
        st.rerun()

# ------------------------------------------------
# 9. Process Query Function
# ------------------------------------------------
def process_query(query):
    """Process a user query and update session state"""
    st.session_state["chat_history"].append({"role": "user", "text": query})
    
    # Set session to None for first message
    if len(st.session_state["chat_history"]) == 1:
        st.session_state["session"] = None
    
    # Call backend
    with st.spinner("Reasoning..."):
        result = run_query(
            query, 
            st.session_state["client_id"], 
            st.session_state["session_id"],  
            previous_session=st.session_state.get("session")
        )
    
    session = result.get("session", {})
    st.session_state["session"] = session
    response_text = result["final_response"].get("text", "Sorry, I couldn't process that.")
    escaped_response_text = escape_dollar_signs(response_text)
    st.session_state["chat_history"].append({"role": "assistant", "text": escaped_response_text})
   
    # Store latest portfolio/market data in session
    st.session_state["last_portfolio"] = result.get("structured_response", {})
    st.session_state["last_market"] = result.get("market_response", {})
    st.session_state["debug_data"] = {
        "query": query,
        "structured_response": result["final_response"].get("data", {}).get("portfolio", {}),
        "market_response": result["final_response"].get("data", {}).get("market_response", {}),
    }

# ------------------------------------------------
# 10. Footer
# ------------------------------------------------
def footer():
    st.markdown("---")
    st.caption("Built for Portfolio Intelligence | v1.0 | All data is for demonstration purposes only.")

# ------------------------------------------------
# 11. App Layout
# ------------------------------------------------
def app_main():
    header()
    client_ids = ["CLT-001", "CLT-002", "CLT-003", "CLT-004", "CLT-005", "CLT-007", "CLT-009", "CLT-010"] 
    session_sidebar(client_ids)

    if "client_id" in st.session_state:
        portfolio_data = st.session_state.get("last_portfolio", {})
        market_data = st.session_state.get("last_market", {})

        portfolio_snapshot(portfolio_data)
        market_snapshot(market_data)
        chat_interface()

        debug_data = st.session_state.get("debug_data", {})
        debug_panel(debug_data)

    footer()

# ------------------------------------------------
# 12. Entry Point
# ------------------------------------------------
if __name__ == "__main__":
    st.set_page_config(page_title="Portfolio Intelligence", layout="wide")
    app_main()