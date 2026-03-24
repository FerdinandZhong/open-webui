"""
Fraud Detection Workflow Pipeline for Cloudera Agent Studio Integration

A pipe that submits an attachment (e.g. invoice / transaction CSV path) to the
fraud-detection workflow, then streams the results back in real-time.

Usage in Open WebUI chat:
  - Type a session-relative attachment path as your message, e.g.:
      session/abc123/invoice.csv
  - Or leave the chat message empty / type anything and set DEFAULT_ATTACHMENT
    in the valve to a pre-configured path.
"""

import requests
import time
import json
import logging
from pydantic import BaseModel, Field
from typing import Generator, Union, Optional, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Pipe:
    """Fraud Detection Workflow Pipeline for Cloudera Agent Studio"""

    class Valves(BaseModel):
        MODEL_ENDPOINT: str = Field(
            default="",
            description="Base URL of the CML fraud-detection workflow (required)",
        )
        CDSW_APIV2_KEY: str = Field(
            default="",
            description="Your Cloudera API key (required)",
        )
        DEFAULT_ATTACHMENT: str = Field(
            default="",
            description=(
                "Default attachment path sent to the workflow when the chat "
                "message is empty or does not look like a file path. "
                "Example: session/abc123/transactions.csv"
            ),
        )
        POLL_INTERVAL: int = Field(
            default=5,
            description="Seconds between event-poll requests",
        )
        MAX_POLL_INTERVAL: int = Field(
            default=15,
            description="Maximum seconds between polls (exponential backoff cap)",
        )
        OVERALL_TIMEOUT: int = Field(
            default=300,
            description="Overall timeout in seconds before aborting",
        )
        REQUEST_TIMEOUT: int = Field(
            default=30,
            description="Per-request HTTP timeout in seconds",
        )
        MAX_RETRIES: int = Field(
            default=3,
            description="Max retry attempts for failed HTTP requests",
        )
        ENABLE_DEBUG_LOGGING: bool = Field(
            default=False,
            description="Enable verbose debug logging",
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "cloudera_fraud_detection"
        self.name = "Cloudera Fraud Detection"
        self.valves = self.Valves()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate_config(self) -> tuple[bool, Optional[str]]:
        if not self.valves.CDSW_APIV2_KEY:
            return False, "CDSW_APIV2_KEY is required"
        if not self.valves.MODEL_ENDPOINT:
            return False, "MODEL_ENDPOINT is required"
        return True, None

    def _headers(self, json_body: bool = True) -> Dict[str, str]:
        h = {"Authorization": f"Bearer {self.valves.CDSW_APIV2_KEY}"}
        if json_body:
            h["Content-Type"] = "application/json"
        return h

    def _retry_request(self, method: str, url: str, description: str, **kwargs) -> requests.Response:
        """HTTP request with retry + exponential backoff."""
        kwargs.setdefault("timeout", self.valves.REQUEST_TIMEOUT)
        for attempt in range(self.valves.MAX_RETRIES):
            try:
                resp = getattr(requests, method)(url, **kwargs)
                resp.raise_for_status()
                return resp
            except requests.exceptions.Timeout:
                if attempt == self.valves.MAX_RETRIES - 1:
                    raise Exception(f"{description} timed out after {self.valves.MAX_RETRIES} attempts")
                logger.warning(f"{description} timeout (attempt {attempt + 1}), retrying...")
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else None
                if status and status < 500:
                    raise Exception(f"{description} failed: {e}")
                if attempt == self.valves.MAX_RETRIES - 1:
                    raise Exception(f"{description} failed after {self.valves.MAX_RETRIES} attempts: {e}")
                logger.warning(f"{description} HTTP error (attempt {attempt + 1}), retrying...")
            except Exception as e:
                if attempt == self.valves.MAX_RETRIES - 1:
                    raise Exception(f"{description} failed: {e}")
                logger.warning(f"{description} error (attempt {attempt + 1}): {e}")

            time.sleep(self.valves.MAX_RETRIES ** attempt * 0.5)

    # ------------------------------------------------------------------
    # Workflow steps
    # ------------------------------------------------------------------

    def _create_session(self) -> str:
        """Create a new workflow session and return session_id."""
        resp = self._retry_request(
            "post",
            f"{self.valves.MODEL_ENDPOINT}/api/workflow/createSession",
            "Session creation",
            headers=self._headers(),
            json={},
        )
        session_id = resp.json().get("session_id")
        if not session_id:
            raise Exception(f"No session_id in response: {resp.json()}")
        logger.info(f"Session created: {session_id}")
        return session_id

    def _kickoff(self, attachments: str) -> str:
        """Kick off the fraud-detection workflow and return trace_id."""
        payload = {"inputs": {"Attachments": attachments}}
        if self.valves.ENABLE_DEBUG_LOGGING:
            logger.debug(f"Kickoff payload: {json.dumps(payload, indent=2)}")

        resp = self._retry_request(
            "post",
            f"{self.valves.MODEL_ENDPOINT}/api/workflow/kickoff",
            "Workflow kickoff",
            headers=self._headers(),
            json=payload,
        )
        trace_id = resp.json().get("trace_id")
        if not trace_id:
            raise Exception(f"No trace_id in kickoff response: {resp.json()}")
        logger.info(f"Workflow started: trace_id={trace_id}")
        return trace_id

    def _poll_events(self, trace_id: str) -> Generator[str, None, None]:
        """Poll /api/workflow/events and stream content as it arrives."""
        start_time = time.time()
        seen_ts: set = set()
        seen_content: set = set()
        poll_interval = self.valves.POLL_INTERVAL
        consecutive_empty = 0

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.valves.OVERALL_TIMEOUT:
                yield f"\n\n⏰ Timed out after {int(elapsed)}s\n"
                return

            try:
                resp = requests.get(
                    f"{self.valves.MODEL_ENDPOINT}/api/workflow/events",
                    headers=self._headers(json_body=False),
                    params={"trace_id": trace_id},
                    timeout=self.valves.REQUEST_TIMEOUT,
                )

                if resp.status_code == 200:
                    events = resp.json().get("events", [])

                    if not events:
                        consecutive_empty += 1
                        if consecutive_empty > 3:
                            poll_interval = min(poll_interval * 1.2, self.valves.MAX_POLL_INTERVAL)
                    else:
                        consecutive_empty = 0
                        poll_interval = self.valves.POLL_INTERVAL

                    for event in events:
                        ts = event.get("timestamp")
                        if not ts or ts in seen_ts:
                            continue
                        seen_ts.add(ts)

                        e_type = event.get("type", "")
                        content = (
                            event.get("response") or
                            event.get("output") or
                            event.get("outout") or  # API typo
                            ""
                        )

                        # Failure events
                        if e_type in ["crew_kickoff_failed", "workflow_failed", "error"]:
                            err = event.get("error", "Unknown error")
                            yield f"\n\n❌ **Workflow failed**: {err}\n"
                            if isinstance(event.get("metadata"), dict) and "error" in event["metadata"]:
                                yield f"```\n{event['metadata']['error']}\n```\n"
                            logger.error(f"Workflow failed: {e_type} — {err}")
                            return

                        # Stream content (deduplicated)
                        if content and e_type in ["task_completed", "task_output", "crew_kickoff_completed"]:
                            h = hash(content)
                            if h not in seen_content:
                                seen_content.add(h)
                                yield content

                        # Completion
                        if e_type == "crew_kickoff_completed":
                            return

                elif resp.status_code >= 500:
                    logger.warning(f"Server error during polling: {resp.status_code}")
                else:
                    yield f"\n\n❌ Unexpected HTTP {resp.status_code}\n"
                    return

            except requests.exceptions.Timeout:
                logger.warning("Polling request timed out, retrying...")
            except Exception as e:
                logger.warning(f"Polling error: {e}")

            time.sleep(poll_interval)

    # ------------------------------------------------------------------
    # Open WebUI entry point
    # ------------------------------------------------------------------

    def pipe(self, body: dict, __files__: list = None) -> Union[str, Generator]:
        def stream() -> Generator[str, None, None]:
            try:
                # Config check
                ok, err = self._validate_config()
                if not ok:
                    yield f"❌ **Configuration error**: {err}\n"
                    yield "Set MODEL_ENDPOINT and CDSW_APIV2_KEY in the pipe settings.\n"
                    return

                # Resolve attachment path:
                #   1. Use the last user message if it looks like a file path
                #   2. Fall back to DEFAULT_ATTACHMENT valve
                messages = body.get("messages", [])
                user_msg = messages[-1].get("content", "").strip() if messages else ""

                looks_like_path = "/" in user_msg or user_msg.endswith(
                    (".csv", ".pdf", ".xlsx", ".json", ".txt")
                )
                attachments = user_msg if looks_like_path else self.valves.DEFAULT_ATTACHMENT

                if not attachments:
                    yield (
                        "❌ **No attachment specified.**\n\n"
                        "Either type the attachment path as your message "
                        "(e.g. `session/abc123/invoice.csv`), or set "
                        "**DEFAULT_ATTACHMENT** in the pipe valves.\n"
                    )
                    return

                yield f"🔍 **Fraud Detection Workflow**\n"
                yield f"📎 Attachment: `{attachments}`\n\n"

                # Step 1 — session
                yield "🔄 Creating session...\n"
                try:
                    session_id = self._create_session()
                    yield f"✅ Session: `{session_id}`\n\n"
                except Exception as e:
                    yield f"❌ **Session creation failed**: {e}\n"
                    return

                # Step 2 — kickoff
                yield "🚀 Starting workflow...\n\n---\n\n"
                try:
                    trace_id = self._kickoff(attachments)
                except Exception as e:
                    yield f"❌ **Kickoff failed**: {e}\n"
                    return

                # Step 3 — stream results
                yield from self._poll_events(trace_id)

            except Exception as e:
                logger.error(f"Pipeline error: {e}", exc_info=True)
                yield f"❌ **Critical error**: {e}\n"
                if self.valves.ENABLE_DEBUG_LOGGING:
                    import traceback
                    yield f"```\n{traceback.format_exc()}\n```\n"

        return stream()
