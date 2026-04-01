from pathlib import Path
import re
import time

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8503"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "assets" / "help"
VIEWPORT = {"width": 1600, "height": 1400}

PAGE_SPECS = [
    {
        "nav_label": "🏠  Home",
        "wait_text": "Social Inclusion Document Analyzer",
        "filename": "home.png",
        "focus_text": "Document Scope",
        "padding_top": 250,
        "clip_height": 900,
    },
    {
        "nav_label": "📄  Documents",
        "wait_text": "Document Management",
        "filename": "documents.png",
        "focus_text": "Document Library",
        "padding_top": 320,
        "clip_height": 920,
    },
    {
        "nav_label": "📋  Templates",
        "wait_text": "Template Manager",
        "filename": "templates.png",
        "focus_text": "Define a New Report Template",
        "padding_top": 220,
        "clip_height": 900,
    },
    {
        "nav_label": "📊  Reports",
        "wait_text": "Report Generator",
        "filename": "reports.png",
        "focus_text": "Generated Reports",
        "padding_top": 320,
        "clip_height": 930,
    },
    {
        "nav_label": "🔍  Changes",
        "wait_text": "Change Monitor",
        "filename": "changes.png",
        "focus_text": "Compare Two Document Versions",
        "padding_top": 260,
        "clip_height": 930,
    },
    {
        "nav_label": "🗺️  Map",
        "wait_text": "Geospatial View",
        "filename": "map.png",
        "focus_text": "Location list",
        "padding_top": 320,
        "clip_height": 950,
    },
    {
        "nav_label": "🔎  Compliance",
        "wait_text": "Semantic Compliance Analysis",
        "filename": "compliance.png",
        "focus_text": "Semantic Compliance Analysis",
        "padding_top": 100,
        "clip_height": 980,
    },
    {
        "nav_label": "🌐  Sources",
        "wait_text": "Reference Sources Catalogue",
        "filename": "sources.png",
        "focus_text": "Current DB template snapshot",
        "padding_top": 330,
        "clip_height": 940,
    },
    {
        "nav_label": "⚖️  HRBA match",
        "wait_text": "HRBA",
        "filename": "hrba.png",
        "focus_text": "HRBA",
        "padding_top": 120,
        "clip_height": 960,
    },
    {
        "nav_label": "🧾  HRBA Insights",
        "wait_text": "HRBA Insights",
        "filename": "hrba_insights.png",
        "focus_text": "Saved Justifications",
        "padding_top": 240,
        "clip_height": 920,
    },
    {
        "nav_label": "❓  Help",
        "wait_text": "Help & Documentation",
        "filename": "help.png",
        "focus_text": "KPIs & Charts",
        "padding_top": 220,
        "clip_height": 950,
    },
]


def wait_for_streamlit_ready(page, wait_text: str) -> None:
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(1800)
    page.get_by_text(wait_text, exact=False).first.wait_for(timeout=30000)
    page.wait_for_timeout(1200)


def click_sidebar_link(page, label: str) -> None:
    link = page.locator("[data-testid='stPageLink'] a").filter(has_text=label).first
    link.wait_for(timeout=15000)
    link.click()


def dismiss_dialogs(page) -> None:
    possible_buttons = [
        "Close",
        "Dismiss",
        "OK",
    ]
    for button_text in possible_buttons:
        button = page.get_by_role("button", name=re.compile(button_text, re.I))
        if button.count() > 0:
            try:
                button.first.click(timeout=500)
            except Exception:
                pass


def _main_container(page):
    selectors = [
        "[data-testid='stMainBlockContainer']",
        "section.main .block-container",
        "div.block-container",
        "[data-testid='stAppViewContainer']",
        "body",
    ]
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() > 0:
                return locator
        except Exception:
            continue
    return page.locator("body").first


def _capture_focused_region(page, spec: dict) -> None:
    main_container = _main_container(page)
    try:
        main_container.wait_for(timeout=5000)
    except PlaywrightTimeoutError:
        pass

    focus_text = spec.get("focus_text") or spec["wait_text"]
    focus_locator = page.get_by_text(focus_text, exact=False).first

    try:
        focus_locator.wait_for(timeout=7000)
        focus_locator.scroll_into_view_if_needed(timeout=2000)
    except PlaywrightTimeoutError:
        pass

    page.wait_for_timeout(900)
    main_box = main_container.bounding_box()
    focus_box = focus_locator.bounding_box() if focus_locator.count() else None

    if not main_box:
        page.screenshot(path=str(OUTPUT_DIR / spec["filename"]), full_page=False)
        return

    top = main_box["y"]
    if focus_box:
        top = max(main_box["y"], focus_box["y"] - spec.get("padding_top", 180))

    left = max(main_box["x"] - 10, 0)
    width = min(main_box["width"] + 20, VIEWPORT["width"] - left)
    height = min(spec.get("clip_height", 900), VIEWPORT["height"] - 20)

    clip = {
        "x": left,
        "y": max(top, 0),
        "width": max(width, 200),
        "height": max(height, 200),
    }
    page.screenshot(path=str(OUTPUT_DIR / spec["filename"]), clip=clip)


def capture_all() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        page = context.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded")
        wait_for_streamlit_ready(page, PAGE_SPECS[0]["wait_text"])
        dismiss_dialogs(page)

        for index, spec in enumerate(PAGE_SPECS):
            if index > 0:
                click_sidebar_link(page, spec["nav_label"])
                try:
                    wait_for_streamlit_ready(page, spec["wait_text"])
                except PlaywrightTimeoutError:
                    page.wait_for_timeout(2500)
            else:
                page.wait_for_timeout(800)

            _capture_focused_region(page, spec)
            print(f"saved {spec['filename']}")

        context.close()
        browser.close()


if __name__ == "__main__":
    started = time.time()
    capture_all()
    print(f"completed in {time.time() - started:.1f}s")
