import streamlit as st
from document_processing.processors.hrba_matcher import HRBAMatcher
from config import Config

st.title("⚖️ HRBA — AAAQ Matcher")

st.markdown(
    """
    Use the HRBA matcher to scan text for AAAQ indicators (Availability, Accessibility,
    Acceptability, Quality). Paste text below or upload/choose a processed document.
    """
)

matcher = HRBAMatcher()

text_input = st.text_area("Document text or excerpt", height=300)

if st.button("Analyze text"):
    if not text_input or not text_input.strip():
        st.warning("Please paste or enter some text to analyze.")
    else:
        with st.spinner("Analyzing text for HRBA indicators..."):
            insights = matcher.extract_hrba_insights(text_input)

        if not insights:
            st.info("No high-confidence HRBA matches found. Try a longer excerpt or adjust keywords.")
        else:
            st.subheader("Detected HRBA passages")
            for i, ins in enumerate(insights, start=1):
                st.markdown(f"**{i}. {ins['category']}** — score: {ins['score']}")
                st.write(ins["text"]) 

            # Simple summary counts
            counts = {}
            for ins in insights:
                counts[ins["category"]] = counts.get(ins["category"], 0) + 1

            st.markdown("---")
            st.subheader("Summary")
            for cat, cnt in counts.items():
                st.write(f"- {cat}: {cnt} passages")

st.markdown("---")
st.caption(f"spaCy model: {Config.SPACY_MODEL}")
