#!/usr/bin/env python3
"""
Local test script for the Invoice Advanced Parser workflow.

Multi-agent CrewAI workflow for Key Information Extraction (KIE) from invoices
and receipts using dual OCR (PaddleOCR + RolmOCR) with AI reconciliation.

Architecture:
  Document Processing Manager (Hierarchical Coordinator)
    ├── Document Extraction Specialist  →  agentic_kie_tool
    │       Paddle Agent → Rolm Agent → Master Agent (reconciliation)
    └── Document Q&A Analyst  (uses extracted context, no tools)

Usage:
  # Basic extraction with a local invoice image
  python local_test_invoice_parser.py -f invoice.png

  # Ask a specific question after uploading
  python local_test_invoice_parser.py -f invoice.png -u "What is the total amount and tax?"

  # Multi-turn: provide prior conversation context
  python local_test_invoice_parser.py -u "What currency is used?" -c '[{"role":"assistant","content":"Total: 150.00 USD"}]'

  # No file — just a text question (workflow may ask you to upload first)
  python local_test_invoice_parser.py -u "Extract all canonical fields"

Environment variables:
  CDSW_APIV2_KEY  - Your CML API key (required)
  MODEL_ENDPOINT  - Override the default endpoint URL (optional)
"""

import requests
import time
import sys
import os
import json
import argparse

# --- CONFIGURATION ---
MODEL_ENDPOINT = os.environ.get(
    "MODEL_ENDPOINT",
    "https://workflow-67dd572e-ad8c-45dd-8db9-75ea9f1c952f.ml-7b697bed-c8f.gr-docpr.a465-9q4k.cloudera.site",
)
CDSW_APIV2_KEY = os.environ.get("CDSW_APIV2_KEY", "")

DEFAULT_USER_INPUT = "Please extract all fields from this invoice."
DEFAULT_CONTEXT = "[]"
# ---------------------


def upload_file(endpoint: str, session_id: str, session_directory: str, file_path: str, headers_auth: dict) -> str:
    """
    Upload a local file to the workflow session.

    Uses session_directory from the createSession response to build the target
    path, e.g. 'agent-studio/studio-data/workflows/.../session/<id>/invoice.png'
    """
    filename = os.path.basename(file_path)
    # session_directory already ends with '/' per the API spec
    target_path = f"{session_directory}{filename}"

    print(f"[*] Uploading '{filename}' to session {session_id}...")

    with open(file_path, "rb") as fh:
        file_bytes = fh.read()

    # Detect a basic MIME type from extension
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pdf": "application/pdf",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }
    mime_type = mime_map.get(ext, "application/octet-stream")

    upload_res = requests.post(
        f"{endpoint}/api/file/upload",
        headers=headers_auth,                       # no Content-Type — multipart sets its own
        params={"session_id": session_id},
        data={"session_id": session_id, "targetPath": target_path},
        files={"file": (filename, file_bytes, mime_type)},
        timeout=60,
    )

    if upload_res.status_code != 200:
        raise RuntimeError(
            f"File upload failed ({upload_res.status_code}): {upload_res.text}"
        )

    print(f"[+] File uploaded. Target path: {target_path}")
    return target_path


def run_test(user_input: str, context: str, file_path: str = ""):
    """Run the Invoice Advanced Parser workflow test."""

    if not CDSW_APIV2_KEY:
        print("[-] Error: CDSW_APIV2_KEY environment variable not set")
        print("    Set it with: export CDSW_APIV2_KEY='your-api-key'")
        return

    headers = {
        "Authorization": f"Bearer {CDSW_APIV2_KEY}",
        "Content-Type": "application/json",
    }
    headers_auth = {"Authorization": f"Bearer {CDSW_APIV2_KEY}"}  # no Content-Type (used for multipart)

    print("--- 🧾 Starting Invoice Advanced Parser Workflow Test ---")
    print(f"    Endpoint:   {MODEL_ENDPOINT}")
    print(f"    File:       {file_path or '(none)'}")
    print(f"    User Input: {user_input}")
    print(f"    Context:    {context}")
    print()

    # 1. CREATE SESSION
    try:
        print("[*] Step 1: Creating Workflow Session...")
        session_res = requests.post(
            f"{MODEL_ENDPOINT}/api/workflow/createSession",
            headers=headers,
            json={},
            timeout=30,
        )

        if session_res.status_code != 200:
            print(f"[-] Session Creation Failed (Status {session_res.status_code})")
            print(f"    Response: {session_res.text}")
            return

        session_data = session_res.json()
        session_id = session_data.get("session_id")
        session_directory = session_data.get("session_directory", "")

        if not session_id:
            print(f"[-] Error: No session_id in response: {session_data}")
            return

        print(f"[+] Session Created: {session_id}")
        if session_directory:
            print(f"    Directory: {session_directory}")

    except Exception as e:
        print(f"[-] Connection Error during Session Creation: {e}")
        return

    # 2. OPTIONAL FILE UPLOAD
    uploaded_path = ""
    if file_path:
        if not os.path.exists(file_path):
            print(f"[-] Error: File not found: {file_path}")
            return
        try:
            uploaded_path = upload_file(MODEL_ENDPOINT, session_id, session_directory, file_path, headers_auth)
        except Exception as e:
            print(f"[-] Upload Error: {e}")
            return

    # 3. KICKOFF WORKFLOW
    try:
        print(f"\n[*] Step 2: Kicking off Invoice Parser workflow...")

        # The manager agent expects user_input + context (chat-style inputs).
        # When a file was uploaded, mention it in user_input so the manager
        # agent knows to display and process it.
        effective_input = user_input
        if uploaded_path:
            effective_input = f"{user_input}\n\nAttached file path: {uploaded_path}"

        payload = {
            "inputs": {
                "user_input": effective_input,
                "context": context,
            }
        }

        print(f"    Payload: {json.dumps(payload, indent=2)}")

        kick_res = requests.post(
            f"{MODEL_ENDPOINT}/api/workflow/kickoff",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if kick_res.status_code != 200:
            print(f"[-] Kickoff Failed ({kick_res.status_code}): {kick_res.text}")
            return

        trace_id = kick_res.json().get("trace_id")
        if not trace_id:
            print(f"[-] Error: No trace_id in response: {kick_res.json()}")
            return

        print(f"[+] Workflow started. Trace ID: {trace_id}\n")

    except Exception as e:
        print(f"[-] Kickoff Error: {e}")
        return

    # 4. POLL FOR EVENTS
    print("[*] Step 3: Monitoring Workflow Events...")
    seen_ts = set()
    start_time = time.time()

    while True:
        try:
            response = requests.get(
                f"{MODEL_ENDPOINT}/api/workflow/events",
                headers=headers_auth,
                params={"trace_id": trace_id},
                timeout=30,
            )

            if response.status_code == 200:
                events = response.json().get("events", [])

                for event in events:
                    ts = event.get("timestamp")
                    if ts and ts not in seen_ts:
                        seen_ts.add(ts)
                        e_type = event.get("type", "unknown")

                        print(f"\n🔔 EVENT: {e_type.upper()}")
                        print(f"⏰ Timestamp: {ts}")

                        if "response" in event:
                            print(f"📝 Response:\n{event['response']}")
                        elif "output" in event:
                            print(f"📊 Output:\n{event['output']}")
                        elif "outout" in event:  # Handle API typo
                            print(f"📊 Output:\n{event['outout']}")
                        else:
                            clean = {k: v for k, v in event.items()
                                     if k not in ("response", "output", "outout")}
                            print(f"ℹ️  Metadata: {json.dumps(clean, indent=2)}")

                        print("-" * 50)

                        if e_type in ["crew_kickoff_failed", "workflow_failed", "error"]:
                            print(f"\n❌ WORKFLOW FAILED")
                            print(f"   Error: {event.get('error', 'Unknown error')}")
                            if "metadata" in event:
                                print(f"   Details: {json.dumps(event['metadata'], indent=2)}")
                            return

                        if e_type == "crew_kickoff_completed":
                            elapsed = int(time.time() - start_time)
                            print(f"\n🏁 WORKFLOW COMPLETED SUCCESSFULLY ({elapsed}s)")
                            return

            elif response.status_code >= 500:
                print(f"\n[!] Server error {response.status_code}, retrying...")
            else:
                print(f"\n[-] Unexpected status {response.status_code}: {response.text}")
                return

            elapsed = int(time.time() - start_time)
            sys.stdout.write(f"\r    > Polling... ({elapsed}s elapsed)")
            sys.stdout.flush()
            time.sleep(5)

        except KeyboardInterrupt:
            print("\n[!] Test stopped by user.")
            break
        except Exception as e:
            print(f"\n[-] Polling Error: {e}")
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(
        description="Test the Invoice Advanced Parser workflow locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Workflow: Multi-agent KIE (Key Information Extraction) using dual OCR models
  • PaddleOCR  — high-precision text detection + bounding boxes
  • RolmOCR    — vision-language document layout understanding
  • Master Agent — reconciles outputs, produces final key-value pairs

Examples:
  # Upload invoice and extract all fields (default question)
  python local_test_invoice_parser.py -f invoice.png

  # Ask a targeted question
  python local_test_invoice_parser.py -f receipt.jpg -u "What is the tax rate?"

  # Follow-up turn with prior context
  python local_test_invoice_parser.py \\
      -u "Convert the total to EUR" \\
      -c '[{"role":"assistant","content":"Total: 150.00 USD, Tax: 12.50 USD"}]'

  # No file upload — open-ended question
  python local_test_invoice_parser.py -u "What canonical fields do you support?"

Environment variables:
  CDSW_APIV2_KEY  - Your CML API key (required)
  MODEL_ENDPOINT  - Override the default endpoint URL (optional)
""",
    )

    parser.add_argument(
        "-f", "--file",
        default="",
        metavar="PATH",
        help="Path to a local invoice/receipt image to upload (PNG, JPG, PDF, TIFF)",
    )
    parser.add_argument(
        "-u", "--user-input",
        default=DEFAULT_USER_INPUT,
        help=f"Question or instruction for the workflow (default: '{DEFAULT_USER_INPUT}')",
    )
    parser.add_argument(
        "-c", "--context",
        default=DEFAULT_CONTEXT,
        help="Prior conversation context as a JSON array string (default: '[]')",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🧾 Invoice Advanced Parser Workflow Test")
    print("=" * 60)
    print()
    print("Configuration:")
    print(f"  CDSW_APIV2_KEY:  {'***' + CDSW_APIV2_KEY[-4:] if CDSW_APIV2_KEY else '(not set)'}")
    print(f"  MODEL_ENDPOINT:  {MODEL_ENDPOINT}")
    print()

    run_test(
        user_input=args.user_input,
        context=args.context,
        file_path=args.file,
    )


if __name__ == "__main__":
    main()
