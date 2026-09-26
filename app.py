import streamlit as st
import requests
import re
import io
import csv
from datetime import datetime

# Optional PDF text extraction
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Optional Groq AI
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="SLGB AI Assistant",
    page_icon="📑",
    layout="wide"
)


# ============================================================
# CONSTANTS
# ============================================================

BASE_URL = "https://slgb.lgdsindh.gov.pk/qr/"

DEFAULT_START_ID = 360378007

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/153.0 Safari/537.36"
    )
}


# ============================================================
# SESSION STATE
# ============================================================

if "results" not in st.session_state:
    st.session_state.results = []

if "scanned" not in st.session_state:
    st.session_state.scanned = False


# ============================================================
# FUNCTIONS
# ============================================================

def pdf_url(pdf_id):
    """Create official SLGB QR PDF URL."""
    return f"{BASE_URL}{pdf_id}.pdf"


def check_pdf(pdf_id, timeout=10):
    """
    Check whether an SLGB PDF exists.

    Returns:
        dict containing status, URL, size and PDF content.
    """

    url = pdf_url(pdf_id)

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True
        )

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        content = response.content

        # A valid PDF normally begins with %PDF
        is_pdf = (
            response.status_code == 200
            and (
                "application/pdf" in content_type
                or content.startswith(b"%PDF")
            )
        )

        if is_pdf:
            return {
                "id": pdf_id,
                "status": "Found",
                "url": url,
                "size": len(content),
                "content": content
            }

        return {
            "id": pdf_id,
            "status": "Not Found",
            "url": url,
            "size": 0,
            "content": None
        }

    except requests.RequestException as e:
        return {
            "id": pdf_id,
            "status": "Error",
            "url": url,
            "size": 0,
            "content": None,
            "error": str(e)
        }


def extract_pdf_text(pdf_bytes):
    """Extract text from a PDF using PyMuPDF."""

    if not PDF_AVAILABLE:
        return "PDF text extraction library is not installed."

    if not pdf_bytes:
        return ""

    try:
        document = fitz.open(
            stream=pdf_bytes,
            filetype="pdf"
        )

        text_parts = []

        for page in document:
            text_parts.append(page.get_text())

        document.close()

        text = "\n".join(text_parts).strip()

        return text

    except Exception as e:
        return f"Could not extract PDF text: {e}"


def clean_text(text):
    """Clean extracted PDF text."""

    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_metadata(text):
    """
    Attempt to identify common notification information.
    This is deliberately flexible because SLGB documents
    may have different formats.
    """

    cleaned = clean_text(text)

    notification_number = ""

    patterns = [
        r"(?:Notification|Notif\.?|Order)\s*(?:No\.?|Number)?\s*[:\-]?\s*([A-Za-z0-9\/\-\._]+)",
        r"(?:No\.?)\s*[:\-]\s*([A-Za-z0-9\/\-\._]+)"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            cleaned,
            re.IGNORECASE
        )

        if match:
            notification_number = match.group(1)
            break

    date_value = ""

    date_patterns = [
        r"\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b",
        r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b",
        r"\b[A-Za-z]+\s+\d{1,2},\s+\d{4}\b"
    ]

    for pattern in date_patterns:
        match = re.search(
            pattern,
            cleaned
        )

        if match:
            date_value = match.group(0)
            break

    return {
        "notification_number": notification_number,
        "date": date_value,
        "preview": cleaned[:500]
    }


def scan_range(
    start_id,
    number_to_scan,
    stop_after_missing,
    timeout
):
    """
    Scan sequential SLGB PDF IDs.

    The stop_after_missing option prevents unnecessarily
    scanning very large empty ranges.
    """

    found = []
    consecutive_missing = 0

    progress = st.progress(0)
    status = st.empty()

    for index in range(number_to_scan):

        current_id = start_id + index

        status.write(
            f"Checking PDF ID: **{current_id}**"
        )

        result = check_pdf(
            current_id,
            timeout=timeout
        )

        if result["status"] == "Found":

            pdf_text = extract_pdf_text(
                result["content"]
            )

            metadata = extract_metadata(
                pdf_text
            )

            result["text"] = pdf_text
            result.update(metadata)

            found.append(result)

            consecutive_missing = 0

        else:
            consecutive_missing += 1

        progress.progress(
            (index + 1) / number_to_scan
        )

        if consecutive_missing >= stop_after_missing:
            status.write(
                f"Stopped after {stop_after_missing} "
                "consecutive missing PDFs."
            )
            break

    progress.empty()

    return found


def search_results(results, keyword):
    """Search notification text and metadata."""

    if not keyword.strip():
        return results

    keyword = keyword.lower().strip()

    filtered = []

    for item in results:

        searchable = " ".join([
            str(item.get("id", "")),
            str(item.get("notification_number", "")),
            str(item.get("date", "")),
            str(item.get("text", "")),
            str(item.get("preview", ""))
        ]).lower()

        if keyword in searchable:
            filtered.append(item)

    return filtered


def create_csv(results):
    """Create CSV data from results."""

    output = io.StringIO()

    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "status",
            "notification_number",
            "date",
            "url",
            "size",
            "preview"
        ]
    )

    writer.writeheader()

    for item in results:
        writer.writerow({
            "id": item.get("id", ""),
            "status": item.get("status", ""),
            "notification_number": item.get(
                "notification_number", ""
            ),
            "date": item.get("date", ""),
            "url": item.get("url", ""),
            "size": item.get("size", ""),
            "preview": item.get("preview", "")
        })

    return output.getvalue()


def groq_summary(text):
    """Generate an AI summary using Groq."""

    if not GROQ_AVAILABLE:
        return "Groq library is not installed."

    api_key = st.secrets.get(
        "GROQ_API_KEY",
        None
    )

    if not api_key:
        return (
            "GROQ_API_KEY is not configured. "
            "Add it in Streamlit Secrets to enable AI summaries."
        )

    if not text.strip():
        return "No readable text was found in this PDF."

    try:

        client = Groq(
            api_key=api_key
        )

        # Keep input reasonably small.
        text_for_ai = text[:12000]

        prompt = f"""
You are an assistant for Sindh Local Government Department
and Sindh Local Government Board documents.

Summarize the following official notification/order in simple
professional English.

Identify, where available:

1. Notification/order number
2. Date
3. Subject
4. Main decision/order
5. Officers/departments mentioned
6. Important action required
7. Any important deadline

Do not invent information.

DOCUMENT:

{text_for_ai}
"""

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=1000
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI summary failed: {e}"


# ============================================================
# HEADER
# ============================================================

st.title("📑 SLGB AI Assistant")

st.write(
    "Monitor and search publicly accessible "
    "Sindh Local Government Board QR/PDF documents."
)

st.caption(
    "Official PDF source: "
    "https://slgb.lgdsindh.gov.pk/qr/"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Scanner Settings")

    start_id = st.number_input(
        "Starting PDF ID",
        min_value=1,
        value=DEFAULT_START_ID,
        step=1
    )

    number_to_scan = st.slider(
        "Number of IDs to scan",
        min_value=1,
        max_value=500,
        value=50
    )

    stop_after_missing = st.slider(
        "Stop after consecutive missing PDFs",
        min_value=3,
        max_value=50,
        value=10
    )

    timeout = st.slider(
        "Request timeout (seconds)",
        min_value=3,
        max_value=30,
        value=10
    )

    st.divider()

    st.info(
        "Start with a small range such as 20–50 IDs. "
        "Increase the range when needed."
    )


# ============================================================
# SCANNER
# ============================================================

st.subheader("🔎 Scan SLGB QR/PDF IDs")

col1, col2 = st.columns([3, 1])

with col1:

    st.write(
        f"Current range: **{start_id} → "
        f"{start_id + number_to_scan - 1}**"
    )

with col2:

    scan_button = st.button(
        "🚀 Start Scan",
        type="primary",
        use_container_width=True
    )


if scan_button:

    st.session_state.results = []

    with st.spinner(
        "Checking SLGB PDF records..."
    ):

        results = scan_range(
            int(start_id),
            int(number_to_scan),
            int(stop_after_missing),
            int(timeout)
        )

    st.session_state.results = results
    st.session_state.scanned = True

    st.success(
        f"Scan completed. {len(results)} PDF(s) found."
    )


# ============================================================
# RESULTS
# ============================================================

results = st.session_state.results

if results:

    st.divider()

    st.subheader("📋 Found Notifications")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "PDFs Found",
            len(results)
        )

    with col2:
        readable = sum(
            bool(x.get("text", "").strip())
            for x in results
        )

        st.metric(
            "Readable PDFs",
            readable
        )

    with col3:
        st.metric(
            "Latest ID",
            max(x["id"] for x in results)
        )

    st.divider()

    # Search
    search_keyword = st.text_input(
        "🔍 Search notifications",
        placeholder=(
            "Example: Municipal Officer, "
            "appointment, transfer, promotion..."
        )
    )

    filtered_results = search_results(
        results,
        search_keyword
    )

    st.write(
        f"Showing **{len(filtered_results)}** "
        f"result(s)."
    )

    # ========================================================
    # NOTIFICATION CARDS
    # ========================================================

    for item in filtered_results:

        title = (
            item.get("notification_number")
            or f"SLGB PDF {item['id']}"
        )

        with st.expander(
            f"📄 {title} — PDF ID {item['id']}"
        ):

            col1, col2 = st.columns(2)

            with col1:
                st.write(
                    f"**PDF ID:** {item['id']}"
                )

                st.write(
                    f"**Date:** "
                    f"{item.get('date') or 'Not detected'}"
                )

            with col2:

                st.write(
                    f"**File size:** "
                    f"{item.get('size', 0):,} bytes"
                )

                st.link_button(
                    "🌐 Open Official PDF",
                    item["url"]
                )

            st.divider()

            text_content = item.get(
                "text",
                ""
            )

            if text_content.strip():

                st.subheader(
                    "📖 Extracted Text"
                )

                st.text_area(
                    "Document text",
                    text_content,
                    height=250,
                    key=f"text_{item['id']}"
                )

                # AI summary
                if GROQ_AVAILABLE:

                    if st.button(
                        "🤖 Generate AI Summary",
                        key=f"ai_{item['id']}"
                    ):

                        with st.spinner(
                            "Generating summary..."
                        ):

                            summary = groq_summary(
                                text_content
                            )

                        st.subheader(
                            "🤖 AI Summary"
                        )

                        st.write(summary)

            else:

                st.warning(
                    "No readable text was extracted. "
                    "The PDF may be scanned/image-based."
                )


    # ========================================================
    # DOWNLOAD CSV
    # ========================================================

    st.divider()

    csv_data = create_csv(
        filtered_results
    )

    st.download_button(
        "⬇️ Download Results as CSV",
        data=csv_data,
        file_name=(
            f"slgb_results_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        ),
        mime="text/csv"
    )


elif st.session_state.scanned:

    st.warning(
        "No PDF was found in the selected range."
    )


# ============================================================
# INFORMATION
# ============================================================

st.divider()

with st.expander("ℹ️ About SLGB AI Assistant"):

    st.write(
        """
        **SLGB AI Assistant** is a lightweight monitoring and
        document-search tool for publicly accessible SLGB
        QR/PDF documents.

        It does not bypass authentication or restricted systems.
        It only checks publicly accessible PDF URLs.

        The application can:

        • Scan sequential QR/PDF IDs  
        • Detect available PDF documents  
        • Extract readable PDF text  
        • Search notifications  
        • Open official PDFs  
        • Export results to CSV  
        • Generate optional AI summaries using Groq
        """
    )

st.caption(
    "SLGB AI Assistant • Built with Streamlit"
)

### 2. `requirements.txt`

text
streamlit
requests
PyMuPDF
groq

