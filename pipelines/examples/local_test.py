import requests
import time
import sys
import os
import json

# --- CONFIGURATION ---
WORKFLOW_ID="6f56e8c5-e60a-4800-adef-2cb9e69ce7f6"
MODEL_ENDPOINT = F"https://workflow-{WORKFLOW_ID}.ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site"
CDSW_APIV2_KEY = os.environ["CML_API_KEY"]  # 1. Replace with your actual key
CSV_FILE_PATH = "temperature_data_small.csv"       # 2. Path to a local CSV file
# ---------------------

def run_test():
    if not os.path.exists(CSV_FILE_PATH):
        print(f"[-] Error: Local file {CSV_FILE_PATH} not found.")
        return

    headers = {"Authorization": f"Bearer {CDSW_APIV2_KEY}"}
    filename = os.path.basename(CSV_FILE_PATH)
    print(f"--- 🚀 Starting Full CML Lifecycle Test ---")

    # 1. CREATE SESSION
    try:
        print("[*] Step 1: Creating Workflow Session...")
        create_session_url = f"{MODEL_ENDPOINT}/api/workflow/createSession"
        session_res = requests.post(
            create_session_url, 
            headers={**headers, "Content-Type": "application/json"},
            timeout=30,
            json={"workflow_id": WORKFLOW_ID}
        )
        
        # Check if the request failed
        if session_res.status_code != 200:
            print(f"[-] Session Creation Failed (Status {session_res.status_code})")
            try:
                # Try to print the detailed JSON error from Cloudera
                print(f"[-] Server Error Message: {session_res.text}")
            except:
                print("[-] Could not parse error response body.")
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

    # 2. UPLOAD FILE (With targetPath)
    try:
        print(f"[*] Step 2: Uploading {filename} with targetPath...")
        upload_url = f"{MODEL_ENDPOINT}/api/file/upload"
        
        # Construct the targetPath using the pattern you provided
        target_path = f"agent-studio/studio-data/deployable_workflows/{WORKFLOW_ID}/session/{session_id}/{filename}"
        
        # Fields to be sent as part of the multipart form
        # We pass session_id and targetPath as form data fields
        data = {
            "session_id": session_id,
            "targetPath": target_path
        }
        
        with open(CSV_FILE_PATH, 'rb') as f:
            files = {'file': (filename, f, 'text/csv')}
            
            # NOTE: session_id is often required in BOTH params and data for some CML versions
            upload_res = requests.post(
                upload_url, 
                headers=headers, 
                params={"session_id": session_id}, # Query param
                data=data,                         # Form data
                files=files,                       # File data
                timeout=60
            )
        
        if upload_res.status_code != 200:
            print(f"[-] Upload Failed ({upload_res.status_code}): {upload_res.text}")
            return
            
        print(f"[+] File uploaded successfully to: {target_path}")
    except Exception as e:
        print(f"[-] Upload Error: {e}")
        return

    # 3. KICKOFF WORKFLOW (Updated Syntax)
    try:
        print(f"[*] Step 3: Kicking off workflow with structured payload...")
        kickoff_url = f"{MODEL_ENDPOINT}/api/workflow/kickoff"
        
        # Payload matches your reference exactly
        payload = {
            "inputs": {
                "Attachments": json.dumps([filename]),  # Must be a stringified list
                "question": "analyze the csv to find the lowest temperature",
                "session_id": session_id
            }
        }
        
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

    # 4. POLL FOR EVERY EVENT
    print("[*] Step 4: Monitoring ALL Events (Verbose Mode)...")
    seen_ts = set()
    start_time = time.time()

    while True:
        try:
            response = requests.get(f"{MODEL_ENDPOINT}/api/workflow/events", headers=headers, params={"trace_id": trace_id})
            if response.status_code == 200:
                events = response.json().get("events", [])

                for event in events:
                    ts = event.get("timestamp")
                    if ts not in seen_ts:
                        e_type = event.get("type")

                        print(f"\n🔔 EVENT: {e_type.upper()}")
                        print(f"⏰ Timestamp: {ts}")

                        # Dynamic printing based on available keys
                        if "response" in event:
                            print(f"📝 Response Content:\n{event.get('response')}")
                        elif "output" in event:
                            print(f"📊 Output Content:\n{event.get('output')}")
                        elif "outout" in event: # Handling the potential typo in JSON
                            print(f"📊 Output Content (typo-key):\n{event.get('outout')}")
                        else:
                            # Print the raw JSON for metadata events (task started, etc)
                            # We filter out large keys we already checked to keep it clean
                            clean_event = {k: v for k, v in event.items() if k not in ['response', 'output', 'outout']}
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

                        # End test if kickoff is completed
                        if e_type == "crew_kickoff_completed":
                            print("\n🏁 WORKFLOW FULLY COMPLETED.")
                            return

                        seen_ts.add(ts)

            # Simple heartbeat in console
            sys.stdout.write(f"\r    > Polling... ({int(time.time() - start_time)}s elapsed)")
            sys.stdout.flush()
            time.sleep(15)

        except KeyboardInterrupt:
            print("\n[!] Test stopped by user.")
            break
        except Exception as e:
            print(f"\n[-] Polling Error: {e}")
            time.sleep(15)

if __name__ == "__main__":
    run_test()