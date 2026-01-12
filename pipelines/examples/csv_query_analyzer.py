import requests
import time
import json
import os
from pydantic import BaseModel, Field
from typing import Generator, Union


class Pipe:
    class Valves(BaseModel):
        WORKFLOW_ID: str = Field(
            default="db40e298-aeaa-4580-8e38-938758f22053",
            description="The ID of your Cloudera Workflow",
        )
        MODEL_ENDPOINT: str = Field(
            default="https://workflow-db40e298-aeaa-4580-8e38-938758f22053.ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site",
            description="The base URL of your CML workflow",
        )
        CDSW_APIV2_KEY: str = Field(default="", description="Your Cloudera API Key")
        POLL_INTERVAL: int = Field(
            default=5, description="Seconds between polling events"
        )
        OVERALL_TIMEOUT: int = Field(
            default=120, description="Overall timeout in seconds (2 minutes)"
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "cloudera_lifecycle_streamer"
        self.name = "Cloudera Workflow Analyst"
        self.valves = self.Valves()

    def pipe(self, body: dict, __files__: list = None) -> Union[str, Generator]:
        # Extract metadata
        user_message = body.get("messages", [])[-1].get("content", "").strip()

        # Define the generator inside the pipe
        def stream_workflow():
            headers_cml = {
                "Authorization": f"Bearer {self.valves.CDSW_APIV2_KEY}",
                "Content-Type": "application/json",
            }
            start_time = time.time()
            seen_ts = set()

            try:
                # 1. FILE RESOLUTION
                # Using the path identified in your debug logs
                file_path = "/home/cdsw/backend/data/uploads/3f39cc13-5973-4039-be5b-afc55b8f70c1_temperature_data_small.csv"
                filename = "temperature_data_small.csv"

                if not os.path.exists(file_path):
                    yield f"❌ Error: Local file not found at `{file_path}`."
                    return

                with open(file_path, "rb") as f:
                    file_bytes = f.read()

                # 2. CREATE SESSION
                yield "🔄 **Initializing CML Session...**\n"
                session_res = requests.post(
                    f"{self.valves.MODEL_ENDPOINT}/api/workflow/createSession",
                    headers=headers_cml,
                    json={"workflow_id": self.valves.WORKFLOW_ID},
                    timeout=20,
                )
                session_res.raise_for_status()
                session_id = session_res.json().get("session_id")

                # 3. UPLOAD FILE
                yield f"📤 **Uploading {filename}...**\n"
                target_path = f"agent-studio/studio-data/deployable_workflows/{self.valves.WORKFLOW_ID}/session/{session_id}/{filename}"

                # Note: multipart upload does NOT use the 'application/json' content type
                upload_headers = {
                    "Authorization": f"Bearer {self.valves.CDSW_APIV2_KEY}"
                }
                files = {"file": (filename, file_bytes, "text/csv")}
                upload_data = {"session_id": session_id, "targetPath": target_path}

                upload_res = requests.post(
                    f"{self.valves.MODEL_ENDPOINT}/api/file/upload",
                    headers=upload_headers,
                    params={"session_id": session_id},
                    data=upload_data,
                    files=files,
                    timeout=60,
                )
                upload_res.raise_for_status()

                # 4. KICKOFF
                yield "🚀 **Starting Analyst Workflow...**\n\n---\n"
                payload = {
                    "inputs": {
                        "Attachments": json.dumps([filename]),
                        "Task": user_message,
                        "session_id": session_id,
                    }
                }
                kick_res = requests.post(
                    f"{self.valves.MODEL_ENDPOINT}/api/workflow/kickoff",
                    headers=headers_cml,
                    json=payload,
                    timeout=20,
                )
                kick_res.raise_for_status()
                trace_id = kick_res.json().get("trace_id")

                # 5. ASYNC POLLING LOOP
                while True:
                    # Check overall timeout
                    if (time.time() - start_time) > self.valves.OVERALL_TIMEOUT:
                        yield f"\n🛑 **Timeout:** Session exceeded {self.valves.OVERALL_TIMEOUT}s."
                        break

                    # Polling request
                    try:
                        response = requests.get(
                            f"{self.valves.MODEL_ENDPOINT}/api/workflow/events",
                            headers={
                                "Authorization": f"Bearer {self.valves.CDSW_APIV2_KEY}"
                            },
                            params={"trace_id": trace_id},
                            timeout=15,
                        )

                        if response.status_code == 200:
                            events = response.json().get("events", [])
                            for event in events:
                                ts = event.get("timestamp")
                                if ts not in seen_ts:
                                    e_type = event.get("type")

                                    # Yield Content
                                    if "response" in event:
                                        yield f"\n{event['response']}\n"
                                    elif "output" in event:
                                        yield f"\n{event['output']}\n"
                                    elif "outout" in event:
                                        yield f"\n{event['outout']}\n"

                                    if e_type == "crew_kickoff_completed":
                                        return  # Success Exit

                                    seen_ts.add(ts)
                    except Exception:
                        pass  # Silently retry on transient polling errors

                    time.sleep(self.valves.POLL_INTERVAL)

            except Exception as e:
                yield f"\n❌ **Critical Error:** {str(e)}"

        # RETURN THE GENERATOR OBJECT
        return stream_workflow()
