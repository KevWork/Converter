"""Currency converter powered by Frankfurter (api.frankfurter.dev)."""

from __future__ import annotations

import requests
import streamlit as st

API_BASE = "https://api.frankfurter.dev/v2"
DEFAULT_CURRENCIES = ("USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD")

st.set_page_config(
    page_title="Currency Converter",
    page_icon="💱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; max-width: 720px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=86400, show_spinner=False)
def load_currency_catalog() -> dict[str, str]:
    response = requests.get(f"{API_BASE}/currencies", timeout=15)
    response.raise_for_status()
    rows = response.json()
    return {row["iso_code"]: row["name"] for row in rows}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_rates(base: str, quotes: tuple[str, ...]) -> tuple[str, dict[str, float]]:
    if not quotes:
        return "", {}
    params = {"base": base.upper(), "quotes": ",".join(q.upper() for q in quotes)}
    response = requests.get(f"{API_BASE}/rates", params=params, timeout=15)
    response.raise_for_status()
    rows = response.json()
    if not rows:
        return "", {}
    rate_date = rows[0].get("date", "")
    rates = {row["quote"]: float(row["rate"]) for row in rows}
    return rate_date, rates


def format_amount(value: float) -> str:
    if abs(value) >= 1_000_000 or (abs(value) < 0.01 and value != 0):
        return f"{value:,.4f}"
    return f"{value:,.2f}"


def main() -> None:
    st.title("Currency converter")
    st.caption("Live rates from [Frankfurter](https://www.frankfurter.app/) — no API key required.")

    try:
        catalog = load_currency_catalog()
    except requests.RequestException as exc:
        st.error(f"Could not load currency list: {exc}")
        st.stop()

    codes = sorted(catalog.keys())
    default_selection = [c for c in DEFAULT_CURRENCIES if c in catalog]

    with st.container(border=True):
        st.subheader("1. Choose your currencies")
        selected = st.multiselect(
            "Currencies to show",
            options=codes,
            default=default_selection,
            format_func=lambda code: f"{code} — {catalog[code]}",
            placeholder="Search and add currencies…",
            help="Conversions appear for every currency you select here.",
        )

    if len(selected) < 1:
        st.info("Select at least one currency to continue.")
        return

    with st.container(border=True):
        st.subheader("2. Convert an amount")
        col_amount, col_from = st.columns([1, 1])
        with col_amount:
            amount = st.number_input(
                "Amount",
                min_value=0.0,
                value=100.0,
                step=1.0,
                format="%.2f",
            )
        with col_from:
            from_currency = st.selectbox(
                "From",
                options=selected,
                format_func=lambda code: f"{code} — {catalog.get(code, code)}",
            )

    quotes = tuple(sorted(set(selected)))
    try:
        rate_date, rates = fetch_rates(from_currency, quotes)
    except requests.RequestException as exc:
        st.error(f"Could not fetch exchange rates: {exc}")
        return

    if not rates:
        st.warning("No rates returned for the selected currencies.")
        return

    st.subheader("Converted amounts")
    date_note = f" · rate date **{rate_date}**" if rate_date else ""
    st.caption(f"Converting from **{from_currency}**{date_note}")

    ordered = [from_currency] + [c for c in sorted(selected) if c != from_currency]
    table_rows = []
    for code in ordered:
        rate = rates.get(code, 0.0)
        table_rows.append(
            {
                "Code": code,
                "Currency": catalog.get(code, code),
                "Amount": format_amount(amount * rate),
                "Rate": "—" if code == from_currency else f"1 {from_currency} = {rate:.6g} {code}",
            }
        )

    st.dataframe(
        table_rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Amount": st.column_config.TextColumn("Amount", width="medium"),
            "Rate": st.column_config.TextColumn("Exchange rate", width="large"),
        },
    )


if __name__ == "__main__":
    main()
