import os

# Prevent TLS CA bundle path issues on some Windows environments
for var in ["CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"]:
    if var in os.environ:
        del os.environ[var]

import streamlit as st
from pathlib import Path
from datetime import date, timedelta

from services.links_service import run_links_scraper
from services.profile_service import run_profile_scraper

st.set_page_config(page_title="Instagram Scraper UI", layout="wide")

st.title("Instagram Scraper Dashboard")
st.caption("Frontend UI for Profile Scraper and Links Scraper (backend unchanged)")

if "profile_result" not in st.session_state:
    st.session_state["profile_result"] = None
if "links_result" not in st.session_state:
    st.session_state["links_result"] = None
if "profile_filter_mode_prev" not in st.session_state:
    st.session_state["profile_filter_mode_prev"] = "Relative"
if "profile_running" not in st.session_state:
    st.session_state["profile_running"] = False
if "links_running" not in st.session_state:
    st.session_state["links_running"] = False
if "profile_pending" not in st.session_state:
    st.session_state["profile_pending"] = False
if "links_pending" not in st.session_state:
    st.session_state["links_pending"] = False
if "profile_payload" not in st.session_state:
    st.session_state["profile_payload"] = None
if "links_payload" not in st.session_state:
    st.session_state["links_payload"] = None
if "profile_error" not in st.session_state:
    st.session_state["profile_error"] = ""
if "links_error" not in st.session_state:
    st.session_state["links_error"] = ""

profile_tab, links_tab = st.tabs(["Profile Scraper", "Links Scraper"])

with profile_tab:
    st.subheader("Profile Scraper")
    if st.session_state["profile_error"]:
        st.error(st.session_state["profile_error"])
        st.session_state["profile_error"] = ""

    profile_urls_text = st.text_area(
        "Instagram Profile URLs (one per line)",
        height=120,
        placeholder="https://www.instagram.com/username1/\nhttps://www.instagram.com/username2/",
        key="profile_urls_text",
        disabled=st.session_state["profile_running"],
    )
    filter_mode = st.selectbox(
        "Date Filter Mode",
        ["Relative", "Custom Date Range"],
        index=0,
        key="profile_filter_mode",
        disabled=st.session_state["profile_running"],
    )

    if filter_mode != st.session_state.get("profile_filter_mode_prev", "Relative"):
        st.session_state["profile_result"] = None
        st.session_state["profile_filter_mode_prev"] = filter_mode

    with st.form("profile_form"):
        timeline_value = None
        timeline_unit = None
        start_date = None
        end_date = None

        if filter_mode == "Relative":
            c1, c2 = st.columns(2)
            with c1:
                timeline_value = st.number_input(
                    "Timeline Value",
                    min_value=1,
                    value=7,
                    step=1,
                    key="relative_timeline_value",
                    disabled=st.session_state["profile_running"],
                )
            with c2:
                timeline_unit = st.selectbox(
                    "Timeline Unit",
                    ["hours", "days", "weeks", "months"],
                    index=1,
                    key="relative_timeline_unit",
                    disabled=st.session_state["profile_running"],
                )
        else:
            c1, c2 = st.columns(2)
            with c1:
                start_date = st.date_input("Start Date", value=date.today() - timedelta(days=7), key="custom_start_date", disabled=st.session_state["profile_running"])
            with c2:
                end_date = st.date_input("End Date", value=date.today(), key="custom_end_date", disabled=st.session_state["profile_running"])

        submitted_profile = st.form_submit_button("Run Profile Scraper", disabled=st.session_state["profile_running"])

    if submitted_profile and not st.session_state["profile_running"]:
        urls = [x.strip() for x in st.session_state.get("profile_urls_text", "").splitlines() if x.strip()]
        if filter_mode == "Custom Date Range":
            if start_date > end_date:
                st.error("Start Date must be before or equal to End Date.")
            elif end_date > date.today():
                st.error("End Date cannot be in the future.")
            else:
                st.session_state["profile_payload"] = {
                    "urls": urls,
                    "timeline_value": int(timeline_value) if timeline_value else None,
                    "timeline_unit": timeline_unit,
                    "filter_mode": filter_mode,
                    "start_date": start_date,
                    "end_date": end_date,
                }
                st.session_state["profile_running"] = True
                st.session_state["profile_pending"] = True
                st.rerun()
        else:
            st.session_state["profile_payload"] = {
                "urls": urls,
                "timeline_value": int(timeline_value) if timeline_value else None,
                "timeline_unit": timeline_unit,
                "filter_mode": filter_mode,
                "start_date": None,
                "end_date": None,
            }
            st.session_state["profile_running"] = True
            st.session_state["profile_pending"] = True
            st.rerun()

    if st.session_state["profile_running"] and st.session_state["profile_pending"]:
        payload = st.session_state.get("profile_payload") or {}
        try:
            with st.spinner("Running profile scraper. This may take several minutes..."):
                result = run_profile_scraper(
                    payload.get("urls", []),
                    payload.get("timeline_value"),
                    payload.get("timeline_unit"),
                    filter_mode=payload.get("filter_mode", "Relative"),
                    start_date=payload.get("start_date"),
                    end_date=payload.get("end_date"),
                )
            st.session_state["profile_result"] = result
        except Exception as e:
            st.session_state["profile_error"] = str(e)
        finally:
            st.session_state["profile_pending"] = False
            st.session_state["profile_running"] = False
            st.session_state["profile_payload"] = None
            st.rerun()

    if st.session_state["profile_result"]:
        st.success("Profile scraping + preprocessing completed.")
        result = st.session_state["profile_result"]
        processed_excel_path = result.get("processed_excel_path", "")

        st.markdown("### Download Processed Output")
        if processed_excel_path and Path(processed_excel_path).exists():
            st.download_button(
                "Download Excel",
                data=Path(processed_excel_path).read_bytes(),
                file_name=Path(processed_excel_path).name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="profile_download_excel",
            )
        else:
            st.info("Data is not available.")

with links_tab:
    st.subheader("Links Scraper")
    if st.session_state["links_error"]:
        st.error(st.session_state["links_error"])
        st.session_state["links_error"] = ""

    with st.form("links_form"):
        label = st.text_input("Scrape Label", value="ui_links", disabled=st.session_state["links_running"])
        links_text = st.text_area(
            "Instagram Post/Reel Links (one URL per line)",
            height=220,
            placeholder="https://www.instagram.com/p/xxxx/\nhttps://www.instagram.com/reel/yyyy/",
            disabled=st.session_state["links_running"],
        )
        submitted_links = st.form_submit_button("Run Links Scraper", disabled=st.session_state["links_running"])

    if submitted_links and not st.session_state["links_running"]:
        st.session_state["links_payload"] = {"links_text": links_text, "label": label}
        st.session_state["links_running"] = True
        st.session_state["links_pending"] = True
        st.rerun()

    if st.session_state["links_running"] and st.session_state["links_pending"]:
        payload = st.session_state.get("links_payload") or {}
        try:
            with st.spinner("Running links scraper. This may take several minutes..."):
                result = run_links_scraper(payload.get("links_text", ""), payload.get("label", "ui_links"))
            st.session_state["links_result"] = result
        except Exception as e:
            st.session_state["links_error"] = str(e)
        finally:
            st.session_state["links_pending"] = False
            st.session_state["links_running"] = False
            st.session_state["links_payload"] = None
            st.rerun()

    if st.session_state["links_result"]:
        st.success("Links scraping + preprocessing completed.")
        result = st.session_state["links_result"]
        processed_excel_path = result.get("processed_excel_path", "")

        st.markdown("### Download Processed Output")
        if processed_excel_path and Path(processed_excel_path).exists():
            st.download_button(
                "Download Excel",
                data=Path(processed_excel_path).read_bytes(),
                file_name=Path(processed_excel_path).name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="links_download_excel",
            )
        else:
            st.info("Data is not available.")
