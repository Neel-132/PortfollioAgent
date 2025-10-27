# 📊 Portfolio & News Intelligence Agent

A **multi-agent financial intelligence system** that combines **portfolio analytics**, **market intelligence**, and **natural language understanding** to answer user queries like:

- “What are my holdings?”  
- “How is Tesla performing?”  
- “Does Apple’s earnings affect my portfolio?”

The system integrates structured portfolio data, live market APIs, and unstructured knowledge sources (e.g., SEC filings, news) to deliver **context-rich, explainable, and real-time responses**.

---

## 🧭 Key Features

- 🧠 **Multi-Agent Orchestration** — Modular LangGraph-based workflow with specialized agents for classification, planning, data retrieval, and response generation.  
- 📈 **Portfolio + Market Intelligence** — Combines structured portfolio performance with live market news, prices, and filings.  
- 🧠 **Conversational Memory** — Maintains context across multi-turn queries.  
- 🧰 **Fallback Strategies** — Rule-based fallback for classification and function calling to ensure reliability.  
- 🔍 **Validator Agent** — Audits agent outputs and flags inconsistencies for re-execution.  
- 🚀 **Production-Ready** — Scalable, observable, and extensible architecture.

---

## 🏗️ System Architecture

            ┌────────────────────────────┐
            │        API Layer           │
            │ (FastAPI Orchestrator)     │
            └────────────┬───────────────┘
                         │
            ┌────────────▼───────────────┐
            │  Agent Orchestration Layer │
            │ (LangGraph + Agents)       │
            └────────────┬───────────────┘
                         │
            ┌────────────▼───────────────┐
            │       Data Layer           │
            │ (Portfolio DB + APIs)      │
            └────────────┬───────────────┘
                         │
            ┌────────────▼───────────────┐
            │      Model Layer           │
            │ (LLM + Rule Engine)        │
            └────────────┬───────────────┘
                         │
            ┌────────────▼───────────────┐
            │     Memory Layer           │
            │ (Session + Chat History)   │
            └────────────┬───────────────┘
                         │
            ┌────────────▼───────────────┐
            │ Logging & Monitoring Layer │
            │ (Metrics + Observability)  │
            └────────────────────────────┘

## How to run?
In dummy.env file present inside backend, put your GEMINI API KEY and rename it to .env and you're good to go


## Set up
- pip install uv
- uv sync
- streamlit run ui/app.py
