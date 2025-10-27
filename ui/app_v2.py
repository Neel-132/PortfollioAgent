import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import your backend orchestrator
from backend.orchestrator.main_graph import run_query
from backend.utils.helper import escape_markdown, escape_dollar_signs, normalize_portfolio_output

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
# def portfolio_snapshot(portfolio_data):
#     st.sidebar.subheader("Portfolio Overview")

#     if not portfolio_data or portfolio_data.get("status") != "success":
#         st.sidebar.write("No portfolio data loaded.")
#         return

#     results = portfolio_data.get("results", [])
#     try:
#         breakpoint()
#         if results:
#             df = pd.DataFrame(results)
#             st.sidebar.dataframe(df)

#         # sector allocation chart if available
#         if "portfolio_summary" in portfolio_data:
#             alloc = portfolio_data["portfolio_summary"].get("sector_allocations", {})
#             if alloc:
#                 alloc_df = pd.DataFrame({"Sector": list(alloc.keys()), "Allocation": list(alloc.values())})
#                 fig = px.pie(alloc_df, names="Sector", values="Allocation")
#                 st.sidebar.plotly_chart(fig, use_container_width=True)

#     except Exception as e:
#         st.sidebar.write("No portfolio data loaded.")


def portfolio_snapshot(portfolio_data):
    """
    Renders a portfolio snapshot in the Streamlit sidebar based on the
    normalized output from normalize_portfolio_output().
    """
    st.sidebar.subheader("📈 Portfolio Overview")
    if not portfolio_data or portfolio_data.get("status") != "success":
        st.sidebar.write("No portfolio data loaded.")
        return
    results = portfolio_data.get("results", [])
    breakpoint()
    normalized = normalize_portfolio_output(results)
    data_type = normalized["type"]
    data = normalized["data"]
    error = normalized["error"]

    # Handle errors gracefully
    if data_type == "error" or error:
        st.sidebar.error(f"⚠️ Unable to render portfolio snapshot.\n\n{error}")
        if normalized.get("trace"):
            with st.sidebar.expander("Error Traceback"):
                st.sidebar.code(normalized["trace"])
        return

    # Handle empty or invalid response
    if not data:
        st.sidebar.info("No portfolio data available.")
        return

    try:
        # ==========================
        # 1. Sector Allocation View
        # ==========================
        if data_type == "allocation":
            alloc_df = pd.DataFrame({
                "Sector": list(data.keys()),
                "Allocation (%)": list(data.values())
            })
            if alloc_df.empty:
                st.sidebar.info("No sector allocation data found.")
                return

            fig = px.pie(
                alloc_df,
                names="Sector",
                values="Allocation (%)",
                title="Sector Allocation",
            )
            st.sidebar.plotly_chart(fig, use_container_width=True)

        # ==========================
        # 2. Instrument Returns View
        # ==========================
        elif data_type == "returns":
            df = pd.DataFrame(data)
            if df.empty:
                st.sidebar.info("No returns data found.")
                return

            st.sidebar.markdown("### 📊 Instrument Returns")
            st.sidebar.dataframe(df)

            # Bar chart for % return
            if "symbol" in df.columns and "pct_return" in df.columns:
                fig = px.bar(
                    df.sort_values("pct_return", ascending=False),
                    x="symbol",
                    y="pct_return",
                    text="pct_return",
                    title="Returns by Instrument (%)",
                )
                fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                fig.update_layout(xaxis_title="Instrument", yaxis_title="% Return")
                st.sidebar.plotly_chart(fig, use_container_width=True)

        elif data_type == "holdings_list":
            st.sidebar.markdown("### 📦 Holdings (Symbols)")
            if not data:
                st.sidebar.info("No holdings available.")
            else:
                for symbol in data:
                    st.sidebar.write(f"- {symbol}")

        elif data_type == "holdings_detailed":
            st.sidebar.markdown("### 🏦 Detailed Holdings")
            df = pd.DataFrame(data)

            # Handle Timestamps safely
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]) or df[col].apply(lambda x: hasattr(x, 'isoformat')).any():
                    df[col] = df[col].astype(str)

            st.sidebar.dataframe(df)

            # Optional: visualize top holdings by quantity or value if available
            if "symbol" in df.columns and "quantity" in df.columns:
                top_holdings = df.sort_values("quantity", ascending=False)
                fig = px.bar(
                    top_holdings,
                    x="symbol",
                    y="quantity",
                    title="Top Holdings by Quantity",
                    text="quantity"
                )
                fig.update_traces(texttemplate='%{text}', textposition='outside')
                fig.update_layout(xaxis_title="Symbol", yaxis_title="Quantity")
                st.sidebar.plotly_chart(fig, use_container_width=True)

        elif data_type == "holdings_unknown":
            st.sidebar.warning("⚠️ Unrecognized holdings structure.")
            with st.sidebar.expander("Raw Data"):
                st.sidebar.json(data)
        elif data_type == "best_performers":
            st.sidebar.markdown("### 🏆 Best Performers")
            df = pd.DataFrame(data)

            if df.empty:
                st.sidebar.info("No best performer data found.")
            else:
                # Convert timestamps to string
                for col in df.columns:
                    if pd.api.types.is_datetime64_any_dtype(df[col]) or df[col].apply(lambda x: hasattr(x, 'isoformat')).any():
                        df[col] = df[col].astype(str)

                # Display full table
                st.sidebar.dataframe(df)

                # Optional bar chart by pct_return
                if "symbol" in df.columns and "pct_return" in df.columns:
                    df_sorted = df.sort_values("pct_return", ascending=False)
                    fig = px.bar(
                        df_sorted,
                        x="symbol",
                        y="pct_return",
                        text="pct_return",
                        title="Top Performers by % Return"
                    )
                    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                    fig.update_layout(xaxis_title="Symbol", yaxis_title="Return (%)")
                    st.sidebar.plotly_chart(fig, use_container_width=True)

        elif data_type == "worst_performers":
            st.sidebar.markdown("### 📉 Worst Performers")
            df = pd.DataFrame(data)

            if df.empty:
                st.sidebar.info("No worst performer data found.")
            else:
                # Convert timestamps safely
                for col in df.columns:
                    if pd.api.types.is_datetime64_any_dtype(df[col]) or df[col].apply(lambda x: hasattr(x, 'isoformat')).any():
                        df[col] = df[col].astype(str)

                st.sidebar.dataframe(df)

                # Bar chart sorted ascending
                if "symbol" in df.columns and "pct_return" in df.columns:
                    df_sorted = df.sort_values("pct_return", ascending=True)
                    fig = px.bar(
                        df_sorted,
                        x="symbol",
                        y="pct_return",
                        text="pct_return",
                        title="Worst Performers by % Return"
                    )
                    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                    fig.update_layout(xaxis_title="Symbol", yaxis_title="Return (%)")
                    st.sidebar.plotly_chart(fig, use_container_width=True)

        elif data_type == "market_cap_allocation":
            st.sidebar.markdown("### 🏦 Market Cap Allocation")
            allocations = data.get("allocations", {})
            raw = data.get("raw", {})

            if not allocations:
                st.sidebar.info("No market cap allocation data found.")
            else:
                alloc_df = pd.DataFrame({
                    "Market Cap Category": list(allocations.keys()),
                    "Allocation (%)": list(allocations.values())
                })
                fig = px.pie(
                    alloc_df,
                    names="Market Cap Category",
                    values="Allocation (%)",
                    title="Portfolio by Market Cap"
                )
                st.sidebar.plotly_chart(fig, use_container_width=True)

                # Optional: Show symbols under each category
                with st.sidebar.expander("View Symbols by Category"):
                    for cap, details in raw.items():
                        symbols = details.get("symbols", [])
                        if symbols:
                            st.sidebar.write(f"**{cap}**: {', '.join(symbols)}")


        ## Unknown
        else:
            st.sidebar.warning(f"⚠️ Unrecognized data type: `{data_type}`")
            # with st.sidebar.expander("Raw Data"):
            #     st.sidebar.json(data)

    except Exception as e:
        st.sidebar.error(f"Unexpected rendering error: {e}")

        
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