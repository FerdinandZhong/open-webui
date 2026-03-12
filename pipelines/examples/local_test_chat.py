#!/usr/bin/env python3
"""
Local test script for CML chat workflow (no file upload needed).
Tests the workflow with a simple chat interface using user_input and context.
"""

import requests
import time
import sys
import os
import json

# --- CONFIGURATION ---
WORKFLOW_ID = os.environ.get("WORKFLOW_ID", "")
MODEL_ENDPOINT = os.environ.get("MODEL_ENDPOINT", "")
CDSW_APIV2_KEY = os.environ.get("CDSW_APIV2_KEY", "")

# Default user input for testing
DEFAULT_USER_INPUT = "how many tables"
DEFAULT_CONTEXT = "[]"
# ---------------------


def run_test(user_input: str = None, context: str = None):
    """Run the chat workflow test."""

    # Validate configuration
    if not WORKFLOW_ID:
        print("[-] Error: WORKFLOW_ID environment variable not set")
        print("    Set it with: export WORKFLOW_ID='your-workflow-id'")
        return

    if not CDSW_APIV2_KEY:
        print("[-] Error: CML_API_KEY environment variable not set")
        print("    Set it with: export CML_API_KEY='your-api-key'")
        return

    # Build endpoint URL if not provided
    endpoint = MODEL_ENDPOINT
    if not endpoint:
        # Try to construct from WORKFLOW_ID - user may need to adjust the domain
        print("[!] Warning: MODEL_ENDPOINT not set, using default pattern")
        endpoint = f"https://workflow-{WORKFLOW_ID}.ml-efa4d4bc-895.qzhong-1.a465-9q4k.cloudera.site"
        print(f"    Using: {endpoint}")
        print("    Set MODEL_ENDPOINT env var if this is incorrect")

    # Use defaults if not provided
    user_input = user_input or DEFAULT_USER_INPUT
    context = context or DEFAULT_CONTEXT

    headers = {"Authorization": f"Bearer {CDSW_APIV2_KEY}"}

    print(f"--- 🚀 Starting CML Chat Workflow Test ---")
    print(f"    Workflow ID: {WORKFLOW_ID}")
    print(f"    User Input: {user_input}")
    print(f"    Context: {context}")
    print()

    # 1. CREATE SESSION
    try:
        print("[*] Step 1: Creating Workflow Session...")
        create_session_url = f"{endpoint}/api/workflow/createSession"
        session_res = requests.post(
            create_session_url,
            headers={**headers, "Content-Type": "application/json"},
            timeout=30,
            json={"workflow_id": WORKFLOW_ID}
        )

        if session_res.status_code != 200:
            print(f"[-] Session Creation Failed (Status {session_res.status_code})")
            print(f"[-] Server Error: {session_res.text}")
            return

        session_data = session_res.json()
        session_id = session_data.get("session_id")

        if not session_id:
            print(f"[-] Error: No session_id in response: {session_data}")
            return

        print(f"[+] Session Created: {session_id}")
    except Exception as e:
        print(f"[-] Connection Error during Session Creation: {e}")
        return

    # 2. KICKOFF WORKFLOW (Chat format - no file upload needed)
    try:
        print(f"\n[*] Step 2: Kicking off chat workflow...")
        kickoff_url = f"{endpoint}/api/workflow/kickoff"

        # Chat payload format
        payload = {
            "inputs": {
                "user_input": user_input,
                "context": context,
                "session_id": session_id
            }
        }

        print(f"    Payload: {json.dumps(payload, indent=2)}")

        kick_res = requests.post(
            kickoff_url,
            json=payload,
            headers={**headers, "Content-Type": "application/json"},
            timeout=30
        )

        if kick_res.status_code != 200:
            print(f"[-] Kickoff Failed ({kick_res.status_code}): {kick_res.text}")
            return

        trace_id = kick_res.json().get("trace_id")
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
                f"{endpoint}/api/workflow/events",
                headers=headers,
                params={"trace_id": trace_id},
                timeout=30
            )

            if response.status_code == 200:
                events = response.json().get("events", [])

                for event in events:
                    ts = event.get("timestamp")
                    if ts and ts not in seen_ts:
                        e_type = event.get("type", "unknown")

                        print(f"\n🔔 EVENT: {e_type.upper()}")
                        print(f"⏰ Timestamp: {ts}")

                        # Print content based on available keys
                        if "response" in event:
                            print(f"📝 Response:\n{event.get('response')}")
                        elif "output" in event:
                            print(f"📊 Output:\n{event.get('output')}")
                        elif "outout" in event:  # Handle typo in API
                            print(f"📊 Output:\n{event.get('outout')}")
                        else:
                            # Print metadata for other events
                            clean_event = {k: v for k, v in event.items()
                                         if k not in ['response', 'output', 'outout']}
                            print(f"ℹ️ Metadata: {json.dumps(clean_event, indent=2)}")

                        print("-" * 50)

                        # Check for failure events
                        if e_type in ["crew_kickoff_failed", "workflow_failed", "error"]:
                            error_msg = event.get("error", "Unknown error")
                            print(f"\n❌ WORKFLOW FAILED")
                            print(f"   Error: {error_msg}")
                            if "metadata" in event:
                                print(f"   Details: {json.dumps(event.get('metadata'), indent=2)}")
                            return

                        # End on completion
                        if e_type == "crew_kickoff_completed":
                            print("\n🏁 WORKFLOW COMPLETED SUCCESSFULLY")
                            return

                        seen_ts.add(ts)

            # Heartbeat
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
    """Main entry point with argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test CML chat workflow locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use defaults
  python local_test_chat.py

  # Custom user input
  python local_test_chat.py -u "what is the average price?"

  # With context
  python local_test_chat.py -u "what is the total?" -c '[{"table": "sales"}]'

Environment variables:
  WORKFLOW_ID    - Your CML workflow ID (required)
  CML_API_KEY    - Your CML API key (required)
  MODEL_ENDPOINT - Full endpoint URL (optional, built from WORKFLOW_ID if not set)
"""
    )

    parser.add_argument(
        "-u", "--user-input",
        default=DEFAULT_USER_INPUT,
        help=f"User input/question (default: '{DEFAULT_USER_INPUT}')"
    )

    parser.add_argument(
        "-c", "--context",
        default=DEFAULT_CONTEXT,
        help=f"Context as JSON string (default: '{DEFAULT_CONTEXT}')"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🗨️  CML Chat Workflow Test")
    print("=" * 60)
    print()
    print("Environment Setup:")
    print(f"  WORKFLOW_ID:    {WORKFLOW_ID or '(not set)'}")
    print(f"  CML_API_KEY:    {'***' if CDSW_APIV2_KEY else '(not set)'}")
    print(f"  MODEL_ENDPOINT: {MODEL_ENDPOINT or '(will be built from WORKFLOW_ID)'}")
    print()

    run_test(user_input=args.user_input, context=args.context)


if __name__ == "__main__":
    main()
