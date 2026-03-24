#!/usr/bin/env python3
"""
Local test script for the Fraud Detection agent workflow.

Usage:
  python local_test_fraud_detection.py
  python local_test_fraud_detection.py -a "path/to/attachment"

Environment variables:
  CDSW_APIV2_KEY  - Your CML API key (required)
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
    "https://workflow-2a117aee-f64b-42e5-82b9-01e1a8b83d91.ml-e54c7b5e-fcc.qzhong-1.a465-9q4k.cloudera.site"
)
CDSW_APIV2_KEY = os.environ.get("CDSW_APIV2_KEY", "")

# Default attachment (empty = no file)
DEFAULT_ATTACHMENTS = ""
# ---------------------


def run_test(attachments: str = DEFAULT_ATTACHMENTS):
    """Run the fraud detection workflow test."""

    if not CDSW_APIV2_KEY:
        print("[-] Error: CDSW_APIV2_KEY environment variable not set")
        print("    Set it with: export CDSW_APIV2_KEY='your-api-key'")
        return

    headers = {"Authorization": f"Bearer {CDSW_APIV2_KEY}"}

    print(f"--- 🚀 Starting Fraud Detection Workflow Test ---")
    print(f"    Endpoint:    {MODEL_ENDPOINT}")
    print(f"    Attachments: {attachments or '(none)'}")
    print()

    # 1. CREATE SESSION
    try:
        print("[*] Step 1: Creating Workflow Session...")
        session_res = requests.post(
            f"{MODEL_ENDPOINT}/api/workflow/createSession",
            headers={**headers, "Content-Type": "application/json"},
            json={},
            timeout=30,
        )

        if session_res.status_code != 200:
            print(f"[-] Session Creation Failed (Status {session_res.status_code})")
            print(f"    Response: {session_res.text}")
            return

        session_data = session_res.json()
        session_id = session_data.get("session_id")

        if not session_id:
            print(f"[-] Error: No session_id in response: {session_data}")
            return

        print(f"[+] Session Created: {session_id}")
        if session_data.get("session_directory"):
            print(f"    Directory: {session_data['session_directory']}")

    except Exception as e:
        print(f"[-] Connection Error during Session Creation: {e}")
        return

    # 2. KICKOFF WORKFLOW
    try:
        print(f"\n[*] Step 2: Kicking off fraud detection workflow...")

        payload = {
            "inputs": {
                "Attachments": attachments
            }
        }

        print(f"    Payload: {json.dumps(payload, indent=2)}")

        kick_res = requests.post(
            f"{MODEL_ENDPOINT}/api/workflow/kickoff",
            headers={**headers, "Content-Type": "application/json"},
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

    # 3. POLL FOR EVENTS
    print("[*] Step 3: Monitoring Workflow Events...")
    seen_ts = set()
    start_time = time.time()

    while True:
        try:
            response = requests.get(
                f"{MODEL_ENDPOINT}/api/workflow/events",
                headers=headers,
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
                        elif "outout" in event:  # Handle typo in API
                            print(f"📊 Output:\n{event['outout']}")
                        else:
                            clean = {k: v for k, v in event.items()
                                     if k not in ("response", "output", "outout")}
                            print(f"ℹ️  Metadata: {json.dumps(clean, indent=2)}")

                        print("-" * 50)

                        # Check for failure
                        if e_type in ["crew_kickoff_failed", "workflow_failed", "error"]:
                            print(f"\n❌ WORKFLOW FAILED")
                            print(f"   Error: {event.get('error', 'Unknown error')}")
                            if "metadata" in event:
                                print(f"   Details: {json.dumps(event['metadata'], indent=2)}")
                            return

                        # Check for completion
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
        description="Test Fraud Detection agent workflow locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with no attachment
  python local_test_fraud_detection.py

  # Run with an attachment path
  python local_test_fraud_detection.py -a "session/abc123/transactions.csv"

Environment variables:
  CDSW_APIV2_KEY  - Your CML API key (required)
  MODEL_ENDPOINT  - Override the default endpoint URL (optional)
"""
    )

    parser.add_argument(
        "-a", "--attachments",
        default=DEFAULT_ATTACHMENTS,
        help="Attachment path or value (default: empty string)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🔍 Fraud Detection Workflow Test")
    print("=" * 60)
    print()
    print("Configuration:")
    print(f"  CDSW_APIV2_KEY:  {'***' + CDSW_APIV2_KEY[-4:] if CDSW_APIV2_KEY else '(not set)'}")
    print(f"  MODEL_ENDPOINT:  {MODEL_ENDPOINT}")
    print()

    run_test(attachments=args.attachments)


if __name__ == "__main__":
    main()
