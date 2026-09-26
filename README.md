# 📑 SLGB AI Assistant

A lightweight Streamlit application for monitoring and searching publicly accessible Sindh Local Government Board (SLGB) QR/PDF documents.

## Features

* Scan sequential SLGB PDF IDs
* Detect available PDF documents
* Extract readable PDF text
* Search notifications by keyword
* Display notification/order information
* Open the official SLGB PDF
* Export results to CSV
* Optional AI summaries using Groq
* Free/open-source Python libraries
* Designed for Streamlit Cloud deployment

## Official PDF Pattern

The application checks URLs in this format:

`https://slgb.lgdsindh.gov.pk/qr/360378007.pdf`

The number is automatically changed during scanning.

## Technology

* Python
* Streamlit
* Requests
* PyMuPDF
* Groq API

## Deployment

### 1. Create GitHub Repository

Create a new repository, for example:

`slgb-ai-assistant`

Upload:

```text
app.py
requirements.txt
README.md
.gitignore
```

### 2. Deploy on Streamlit Cloud

Connect the GitHub repository to Streamlit Cloud.

Set the main file to:

```text
app.py
```

### 3. Add Groq API Key

In Streamlit Cloud:

**App → Settings → Secrets**

Add:

```toml
GROQ_API_KEY = "YOUR_GROQ_API_KEY"
```

The AI summary function is optional. The scanner and PDF extraction work without a Groq API key.

## How to Use

Enter the first PDF ID.

Example:

```text
360378007
```

Choose the number of IDs to scan.

For example:

```text
50
```

The application will check:

```text
360378007
360378008
360378009
...
360378056
```

Available PDFs will be displayed automatically.

## Important

The application only accesses publicly available PDF URLs. It does not bypass authentication, restricted systems, passwords, or access controls.

Use reasonable scan ranges to avoid unnecessary requests to the official server.

## Future Versions

Possible future features:

* Automatic daily monitoring
* New-notification alerts
* Notification database
* Duplicate detection
* Advanced AI document search
* Urdu/Sindhi document summaries
* Notification categories
* Department/office filtering
* Date filtering
* Automatic change detection
* Email/WhatsApp/Telegram notifications
* Dashboard of newly discovered notifications

```
```
