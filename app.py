"""DataLab Enedis Live — Public Portal Shell.

This is the public Streamlit frontend for the DataLab Live portal.
Strictly PUBLIC-SAFE:
- Contains ZERO business logic, algorithms, or local datasets (no DuckDB, Parquet, or core modules).
- Requires authentication via Username + Password.
- Communicates exclusively server-side with the private DataLab backend via token.
"""

from __future__ import annotations

from typing import Any
import pandas as pd
import pydeck as pdk
import streamlit as st

from api_client import (
    get_bench,
    get_geo,
    get_health,
    get_overview,
    get_radar,
    get_watch,
    is_backend_configured,
)
from auth import (
    is_auth_configured,
    is_authenticated,
    render_login_form,
    render_sidebar_session,
)

DISCLAIMER_TEXT = (
    "ℹ️ **Note méthodologique :** Les modules Radar et Watch produisent des signaux statistiques "
    "descriptifs. Ils n'établissent ni causalité ni inefficacité opérationnelle."
)


def main() -> None:
    """Main application loop with strict multi-layer security gates."""
    st.set_page_config(
        page_title="DataLab Enedis Live",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ---------------------------------------------------------
    # GATE 1: Authentication Configuration Check (Fail-Closed)
    # ---------------------------------------------------------
    if not is_auth_configured():
        st.title("⚡ DataLab Enedis — Live")
        st.error(
            "🔒 **Configuration d'authentification manquante.**\n\n"
            "Le portail ne peut pas démarrer en mode non sécurisé. "
            "Veuillez configurer `LIVE_USERNAME` et `LIVE_PASSWORD_HASH` dans vos secrets."
        )
        st.stop()

    # ---------------------------------------------------------
    # GATE 2: User Authentication Gate
    # ---------------------------------------------------------
    if not is_authenticated():
        render_login_form()
        st.stop()

    # ---------------------------------------------------------
    # Authenticated Session: Sidebar Controls
    # ---------------------------------------------------------
    render_sidebar_session()

    # ---------------------------------------------------------
    # GATE 3: Backend Configuration Check (Fail-Closed)
    # ---------------------------------------------------------
    if not is_backend_configured():
        st.title("⚡ DataLab Enedis — Live")
        st.error(
            "⚠️ **Configuration backend manquante.**\n\n"
            "Les variables `DATALAB_API_URL` et `DATALAB_API_TOKEN` doivent être configurées "
            "dans les secrets du serveur."
        )
        st.stop()

    # ---------------------------------------------------------
    # GATE 4: Backend Health Check
    # ---------------------------------------------------------
    health_data, health_err = get_health(timeout=5)
    if health_err or not health_data or health_data.get("status") != "ok":
        st.title("⚡ DataLab Enedis — Live")
        st.error(
            f"❌ **Backend DataLab indisponible.**\n\n"
            f"Impossible d'établir la liaison sécurisée avec l'API privée ({health_err or 'Statut invalide'})."
        )
        st.stop()

    backend_version = health_data.get("version", "inconnue")

    # ---------------------------------------------------------
    # Application Header
    # ---------------------------------------------------------
    st.title("⚡ DataLab Enedis — Live")
    col_hdr1, col_hdr2, col_hdr3 = st.columns([3, 1, 1])
    with col_hdr1:
        st.caption("Portail analytique Open Data Enedis · Accès sécurisé")
    with col_hdr2:
        st.caption(f"🟢 **API connectée** (v{backend_version})")
    with col_hdr3:
        st.caption("🔒 **Accès sécurisé**")

    # ---------------------------------------------------------
    # Navigation
    # ---------------------------------------------------------
    nav_view = (
        st.segmented_control(
            "Navigation",
            ["Overview", "Bench", "Radar", "Watch"],
            default="Overview",
            label_visibility="collapsed",
        )
        or "Overview"
    )

    # ---------------------------------------------------------
    # View: Overview
    # ---------------------------------------------------------
    if nav_view == "Overview":
        st.subheader("Architecture & Disponibilité")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**Live Portal**")
            st.write("Interface Streamlit publique sécurisée par authentification.")
        with col2:
            st.markdown("**Bench**")
            st.write("Comparaison territoriale de la consommation par commune.")
        with col3:
            st.markdown("**Radar**")
            st.write("Détection de signaux statistiques ajustés aux secteurs.")
        with col4:
            st.markdown("**Watch**")
            st.write("Suivi d'évolution interannuelle et décomposition.")

        st.markdown("---")
        st.subheader("État des données sur le serveur privé")

        overview_data, overview_err = get_overview()
        if overview_err or not overview_data:
            st.warning("Impossible de récupérer l'état des données du backend.")
        else:
            avail_years = overview_data.get("available_years", [])
            for y in (2023, 2024):
                is_avail = y in avail_years
                status_label = "✅ Disponible" if is_avail else "⚠️ Non disponible sur le serveur"
                st.write(f"Millésime {y} : {status_label}")

        st.info(DISCLAIMER_TEXT)

    # ---------------------------------------------------------
    # View: Bench
    # ---------------------------------------------------------
    elif nav_view == "Bench":
        st.header("Bench — Comparaison des communes")
        st.caption("Agrégation et analyse comparative des indicateurs électriques communaux.")

        col_b1, col_b2 = st.columns([1, 3])
        with col_b1:
            selected_year = st.selectbox("Millésime", options=[2024, 2023], index=0)
        with col_b2:
            search_query = st.text_input("Filtrer par commune ou code postal", value="", key="bench_search").strip()

        bench_resp, bench_err = get_bench(year=selected_year, search=search_query)

        if bench_err:
            st.error(bench_err)
        elif not bench_resp or not bench_resp.get("available"):
            st.warning(bench_resp.get("message", f"Données indisponibles pour le millésime {selected_year}."))
        else:
            results = bench_resp.get("items", [])
            total_count = bench_resp.get("total_count", len(results))

            total_conso = sum(
                float(r["total_conso_mwh"]) for r in results if r.get("total_conso_mwh") is not None
            )
            total_sites = sum(
                int(r["total_sites"]) for r in results if r.get("total_sites") is not None
            )

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Communes", f"{total_count:,}")
            col_m2.metric("Consommation totale (MWh)", f"{total_conso:,.2f}")
            col_m3.metric("Total sites", f"{total_sites:,}")

            st.subheader("Top communes par consommation par site")
            chart_candidates = [
                r for r in results
                if r.get("conso_mwh_per_site") is not None and bool(str(r.get("nom_commune") or "").strip())
            ]
            chart_candidates.sort(
                key=lambda r: (-float(r["conso_mwh_per_site"]), str(r.get("code_commune") or ""))
            )
            chart_rows = [
                {
                    "Commune": str(r.get("nom_commune")),
                    "MWh / site": round(float(r["conso_mwh_per_site"]), 2),
                }
                for r in chart_candidates[:15]
            ]
            if chart_rows:
                chart_spec = {
                    "mark": "bar",
                    "encoding": {
                        "y": {
                            "field": "Commune",
                            "type": "nominal",
                            "sort": [r["Commune"] for r in chart_rows],
                            "axis": {"title": "Commune", "labelLimit": 300},
                        },
                        "x": {
                            "field": "MWh / site",
                            "type": "quantitative",
                            "scale": {"zero": True},
                            "axis": {"title": "MWh / site"},
                        },
                        "tooltip": [
                            {"field": "Commune", "type": "nominal"},
                            {"field": "MWh / site", "type": "quantitative"},
                        ],
                    },
                }
                st.vega_lite_chart(chart_rows, chart_spec, width="stretch", height=500)

            # Geographic Map if available
            geo_resp, _ = get_geo()
            if geo_resp and geo_resp.get("available"):
                points = geo_resp.get("points", {})
                map_candidates = [
                    r for r in results
                    if r.get("conso_mwh_per_site") is not None and str(r.get("code_commune") or "") in points
                ]
                map_candidates.sort(
                    key=lambda r: (-float(r["conso_mwh_per_site"]), str(r.get("code_commune") or ""))
                )
                top_map = map_candidates[:250]
                map_rows = [
                    {
                        "latitude": points[str(r.get("code_commune"))]["latitude"],
                        "longitude": points[str(r.get("code_commune"))]["longitude"],
                        "Commune": str(r.get("nom_commune") or points[str(r.get("code_commune"))]["nom_geo"]),
                        "Code": str(r.get("code_commune")),
                        "MWh / site": round(float(r["conso_mwh_per_site"]), 2),
                    }
                    for r in top_map
                ]
                if map_rows:
                    st.subheader("Cartographie des 250 premiers territoires")
                    view_state = pdk.ViewState(latitude=46.6, longitude=2.2, zoom=5)
                    layer = pdk.Layer(
                        "ScatterplotLayer",
                        data=map_rows,
                        get_position="[longitude, latitude]",
                        get_radius=5000,
                        radius_min_pixels=3,
                        get_fill_color=[220, 60, 20, 160],
                        pickable=True,
                    )
                    deck = pdk.Deck(
                        layers=[layer],
                        initial_view_state=view_state,
                        map_style=pdk.map_styles.CARTO_DARK_NO_LABELS,
                        tooltip={"text": "Commune: {Commune}\nCode: {Code}\nMWh/site: {MWh / site}"},
                    )
                    st.pydeck_chart(deck, width="stretch", height=450)

            # Data Table
            st.subheader("Données détaillées")
            table_limit = st.selectbox("Nombre de lignes", options=[25, 50, 100], index=0)
            table_data = [
                {
                    "Code": r.get("code_commune"),
                    "Commune": r.get("nom_commune"),
                    "Consommation (MWh)": round(r["total_conso_mwh"], 2) if r.get("total_conso_mwh") is not None else None,
                    "Sites": r.get("total_sites"),
                    "MWh / site": round(r["conso_mwh_per_site"], 2) if r.get("conso_mwh_per_site") is not None else None,
                }
                for r in results[:table_limit]
            ]
            st.dataframe(pd.DataFrame(table_data), use_container_width=True)

        st.info(DISCLAIMER_TEXT)

    # ---------------------------------------------------------
    # View: Radar
    # ---------------------------------------------------------
    elif nav_view == "Radar":
        st.header("Radar — Signaux statistiques")
        st.caption("Identification des écarts statistiques ajustés au mix sectoriel.")

        radar_resp, radar_err = get_radar(year=2024)
        if radar_err:
            st.error(radar_err)
        elif not radar_resp or not radar_resp.get("available"):
            st.warning(radar_resp.get("message", "Données Radar 2024 indisponibles."))
        else:
            items = radar_resp.get("items", [])
            scored = [r for r in items if r.get("sector_adjusted_score") is not None]

            high_count = sum(1 for r in scored if r.get("signal_reliability") == "high")
            mod_count = sum(1 for r in scored if r.get("signal_reliability") == "moderate")
            max_score = max((float(r["sector_adjusted_score"]) for r in scored), default=0.0)

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Communes scorées", f"{len(scored):,}")
            col_m2.metric("Fiabilité haute", f"{high_count:,}")
            col_m3.metric("Score maximal", f"{max_score:.2f}")

            search_radar = st.text_input("Filtrer par commune", value="", key="radar_search").strip()
            if search_radar:
                term = search_radar.lower()
                items = [
                    r for r in items
                    if term in str(r.get("nom_commune") or "").lower()
                    or term in str(r.get("code_commune") or "").lower()
                ]

            st.dataframe(pd.DataFrame(items[:50]), use_container_width=True)

        st.info(DISCLAIMER_TEXT)

    # ---------------------------------------------------------
    # View: Watch
    # ---------------------------------------------------------
    elif nav_view == "Watch":
        st.header("Watch — Évolution interannuelle")
        st.caption("Signaux de variation statistique entre 2023 et 2024.")

        watch_resp, watch_err = get_watch(ref_year=2024, prev_year=2023)
        if watch_err:
            st.error(watch_err)
        elif not watch_resp or not watch_resp.get("available"):
            st.warning(watch_resp.get("message", "Données Watch indisponibles."))
        else:
            items = watch_resp.get("items", [])
            st.metric("Communes suivies", f"{len(items):,}")
            st.dataframe(pd.DataFrame(items[:50]), use_container_width=True)

        st.info(DISCLAIMER_TEXT)


if __name__ == "__main__":
    main()
