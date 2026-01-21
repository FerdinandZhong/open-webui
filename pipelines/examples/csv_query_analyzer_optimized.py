"""
Optimized CSV Query Analyzer Pipeline for Cloudera Workflow Integration

Improvements:
- Dynamic file handling (supports Open WebUI file uploads)
- Retry logic with exponential backoff
- Better error handling and logging
- Resource cleanup with context managers
- Configurable parameters via valves
- Input validation
- Performance optimizations
"""

import requests
import time
import json
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Generator, Union, Optional, List, Dict, Any
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Pipe:
    """CSV Query Analyzer Pipeline for Cloudera Workflow"""

    class Valves(BaseModel):
        """Configuration parameters"""
        WORKFLOW_ID: str = Field(
            default="db40e298-aeaa-4580-8e38-938758f22053",
            description="The ID of your Cloudera Workflow",
        )
        MODEL_ENDPOINT: str = Field(
            default="https://workflow-6f56e8c5-e60a-4800-adef-2cb9e69ce7f6.ml-dbfc64d1-783.go01-dem.ylcu-atmi.cloudera.site",
            description="The base URL of your CML workflow",
        )
        CDSW_APIV2_KEY: str = Field(
            default="",
            description="Your Cloudera API Key (required)"
        )

        # Timing configuration
        POLL_INTERVAL: int = Field(
            default=5,
            description="Initial seconds between polling events"
        )
        MAX_POLL_INTERVAL: int = Field(
            default=15,
            description="Maximum seconds between polls (for exponential backoff)"
        )
        OVERALL_TIMEOUT: int = Field(
            default=120,
            description="Overall timeout in seconds"
        )
        REQUEST_TIMEOUT: int = Field(
            default=30,
            description="Individual request timeout in seconds"
        )

        # Retry configuration
        MAX_RETRIES: int = Field(
            default=3,
            description="Maximum retry attempts for failed requests"
        )
        RETRY_BACKOFF: float = Field(
            default=1.5,
            description="Exponential backoff multiplier for retries"
        )

        # File handling
        MAX_FILE_SIZE_MB: int = Field(
            default=50,
            description="Maximum file size in MB"
        )
        ALLOWED_EXTENSIONS: str = Field(
            default=".csv,.tsv,.txt",
            description="Comma-separated allowed file extensions"
        )

        # Upload directory fallback
        DEFAULT_UPLOAD_DIR: str = Field(
            default="/home/cdsw/backend/data/uploads",
            description="Default directory to search for uploaded files"
        )

        # Logging
        ENABLE_DEBUG_LOGGING: bool = Field(
            default=False,
            description="Enable detailed debug logging"
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "cloudera_csv_analyzer_optimized"
        self.name = "Cloudera CSV Query Analyzer (Optimized)"
        self.valves = self.Valves()
        self._session_id: Optional[str] = None

    def _validate_config(self) -> tuple[bool, Optional[str]]:
        """Validate pipeline configuration"""
        if not self.valves.CDSW_APIV2_KEY:
            return False, "API Key (CDSW_APIV2_KEY) is required"

        if not self.valves.WORKFLOW_ID:
            return False, "Workflow ID is required"

        if not self.valves.MODEL_ENDPOINT:
            return False, "Model endpoint URL is required"

        return True, None

    def _get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        """Generate request headers"""
        headers = {"Authorization": f"Bearer {self.valves.CDSW_APIV2_KEY}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _retry_request(
        self,
        method: str,
        url: str,
        description: str,
        **kwargs
    ) -> requests.Response:
        """
        Execute HTTP request with retry logic and exponential backoff

        Args:
            method: HTTP method (get, post, etc.)
            url: Request URL
            description: Description for logging
            **kwargs: Additional arguments passed to requests

        Returns:
            Response object

        Raises:
            Exception: If all retries fail
        """
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.valves.REQUEST_TIMEOUT

        for attempt in range(self.valves.MAX_RETRIES):
            try:
                if self.valves.ENABLE_DEBUG_LOGGING:
                    logger.debug(f"[Attempt {attempt + 1}] {description}: {url}")

                response = getattr(requests, method)(url, **kwargs)
                response.raise_for_status()
                return response

            except requests.exceptions.Timeout as e:
                if attempt == self.valves.MAX_RETRIES - 1:
                    raise Exception(f"{description} timed out after {self.valves.MAX_RETRIES} attempts")
                logger.warning(f"{description} timeout (attempt {attempt + 1}), retrying...")

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response else None
                if status_code and status_code < 500:  # Don't retry client errors
                    raise Exception(f"{description} failed: {str(e)}")
                if attempt == self.valves.MAX_RETRIES - 1:
                    raise Exception(f"{description} failed after {self.valves.MAX_RETRIES} attempts: {str(e)}")
                logger.warning(f"{description} error (attempt {attempt + 1}), retrying...")

            except Exception as e:
                if attempt == self.valves.MAX_RETRIES - 1:
                    raise Exception(f"{description} failed: {str(e)}")
                logger.warning(f"{description} error (attempt {attempt + 1}): {str(e)}")

            # Exponential backoff
            if attempt < self.valves.MAX_RETRIES - 1:
                sleep_time = (self.valves.RETRY_BACKOFF ** attempt)
                time.sleep(sleep_time)

    def _resolve_file(self, body: dict, __files__: list = None) -> tuple[str, bytes]:
        """
        Resolve and load file from multiple sources

        Returns:
            Tuple of (filename, file_bytes)

        Raises:
            Exception: If file cannot be resolved or loaded
        """
        # 1. Try to use files uploaded through Open WebUI
        if __files__ and len(__files__) > 0:
            file_info = __files__[0]

            if isinstance(file_info, dict):
                file_path = file_info.get("path") or file_info.get("file_path")
                filename = file_info.get("name") or file_info.get("filename", "uploaded.csv")
            else:
                file_path = str(file_info)
                filename = Path(file_path).name

            if file_path and os.path.exists(file_path):
                return self._load_file(file_path, filename)

        # 2. Try to extract file path from message content
        messages = body.get("messages", [])
        if messages:
            last_message = messages[-1].get("content", "")

            # Look for file paths in message
            for line in last_message.split("\n"):
                potential_path = line.strip()
                if potential_path.startswith("/") or potential_path.startswith("./"):
                    if os.path.exists(potential_path):
                        filename = Path(potential_path).name
                        return self._load_file(potential_path, filename)

        # 3. Search default upload directory
        if os.path.exists(self.valves.DEFAULT_UPLOAD_DIR):
            upload_dir = Path(self.valves.DEFAULT_UPLOAD_DIR)
            allowed_exts = self.valves.ALLOWED_EXTENSIONS.split(",")

            # Find most recent matching file
            csv_files = []
            for ext in allowed_exts:
                csv_files.extend(upload_dir.glob(f"*{ext.strip()}"))

            if csv_files:
                most_recent = max(csv_files, key=lambda p: p.stat().st_mtime)
                return self._load_file(str(most_recent), most_recent.name)

        raise Exception(
            "No CSV file found. Please upload a file or provide a file path in your message."
        )

    def _load_file(self, file_path: str, filename: str) -> tuple[str, bytes]:
        """Load and validate file"""
        path = Path(file_path)

        # Validate extension
        allowed_exts = [ext.strip() for ext in self.valves.ALLOWED_EXTENSIONS.split(",")]
        if path.suffix.lower() not in allowed_exts:
            raise Exception(
                f"File type '{path.suffix}' not allowed. Allowed: {', '.join(allowed_exts)}"
            )

        # Check file size
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.valves.MAX_FILE_SIZE_MB:
            raise Exception(
                f"File size ({file_size_mb:.1f}MB) exceeds limit ({self.valves.MAX_FILE_SIZE_MB}MB)"
            )

        # Read file
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        logger.info(f"Loaded file: {filename} ({file_size_mb:.2f}MB)")
        return filename, file_bytes

    def _create_session(self) -> str:
        """Create CML session"""
        response = self._retry_request(
            "post",
            f"{self.valves.MODEL_ENDPOINT}/api/workflow/createSession",
            "Session creation",
            headers=self._get_headers(),
            json={"workflow_id": self.valves.WORKFLOW_ID},
        )

        session_id = response.json().get("session_id")
        if not session_id:
            raise Exception("Failed to get session_id from response")

        self._session_id = session_id
        logger.info(f"Created session: {session_id}")
        return session_id

    def _upload_file(self, session_id: str, filename: str, file_bytes: bytes) -> None:
        """Upload file to CML session"""
        target_path = (
            f"agent-studio/studio-data/deployable_workflows/"
            f"{self.valves.WORKFLOW_ID}/session/{session_id}/{filename}"
        )

        # Upload with multipart form data (no JSON content-type)
        headers = {"Authorization": f"Bearer {self.valves.CDSW_APIV2_KEY}"}
        files = {"file": (filename, file_bytes, "text/csv")}
        data = {"session_id": session_id, "targetPath": target_path}

        self._retry_request(
            "post",
            f"{self.valves.MODEL_ENDPOINT}/api/file/upload",
            "File upload",
            headers=headers,
            params={"session_id": session_id},
            data=data,
            files=files,
        )

        logger.info(f"Uploaded file: {filename}")

    def _kickoff_workflow(self, session_id: str, filename: str, user_message: str) -> str:
        """Start the workflow execution"""
        payload = {
            "inputs": {
                "Attachments": json.dumps([filename]),
                "Task": user_message,
                "session_id": session_id,
            }
        }

        response = self._retry_request(
            "post",
            f"{self.valves.MODEL_ENDPOINT}/api/workflow/kickoff",
            "Workflow kickoff",
            headers=self._get_headers(),
            json=payload,
        )

        trace_id = response.json().get("trace_id")
        if not trace_id:
            raise Exception("Failed to get trace_id from kickoff response")

        logger.info(f"Workflow started: trace_id={trace_id}")
        return trace_id

    def _poll_events(self, trace_id: str) -> Generator[str, None, None]:
        """Poll for workflow events with exponential backoff and real-time streaming"""
        start_time = time.time()
        seen_timestamps = set()
        poll_interval = self.valves.POLL_INTERVAL
        consecutive_empty_polls = 0

        # Track if we've shown section headers
        thinking_header_shown = False
        results_header_shown = False

        while True:
            # Check overall timeout
            elapsed = time.time() - start_time
            if elapsed > self.valves.OVERALL_TIMEOUT:
                yield f"\n\n⏰ Timeout after {int(elapsed)}s\n"
                break

            try:
                response = requests.get(
                    f"{self.valves.MODEL_ENDPOINT}/api/workflow/events",
                    headers=self._get_headers(),
                    params={"trace_id": trace_id},
                    timeout=self.valves.REQUEST_TIMEOUT,
                )

                if response.status_code == 200:
                    events = response.json().get("events", [])

                    if not events:
                        consecutive_empty_polls += 1
                        # Show heartbeat only after some time with no events
                        if consecutive_empty_polls > 2:
                            elapsed_int = int(time.time() - start_time)
                            yield f" {elapsed_int}s"
                            poll_interval = min(
                                poll_interval * 1.2,
                                self.valves.MAX_POLL_INTERVAL
                            )
                    else:
                        consecutive_empty_polls = 0
                        poll_interval = self.valves.POLL_INTERVAL  # Reset to base interval

                    for event in events:
                        timestamp = event.get("timestamp")
                        if timestamp and timestamp not in seen_timestamps:
                            seen_timestamps.add(timestamp)

                            # Process event content
                            event_type = event.get("type")
                            content = (
                                event.get("response") or
                                event.get("output") or
                                event.get("outout") or  # Handle typo in API
                                ""
                            )

                            # Check for failure events FIRST (before checking for content)
                            if event_type in ["crew_kickoff_failed", "workflow_failed", "error"]:
                                error_msg = event.get("error", "Unknown error")
                                yield f"\n\n❌ **Workflow Failed**: {error_msg}\n"

                                # Include metadata/details if available
                                if "metadata" in event:
                                    metadata = event.get("metadata")
                                    if isinstance(metadata, dict):
                                        if "error" in metadata:
                                            yield f"```\n{metadata['error']}\n```\n"

                                logger.error(f"Workflow failed: {event_type} - {error_msg}")
                                return

                            # Stream thinking/procedure content with header
                            if content and event_type in ["task_started", "task_running", "agent_thinking"]:
                                if not thinking_header_shown:
                                    yield "\n\n### 🔍 Workflow Procedure\n\n"
                                    thinking_header_shown = True
                                yield f"- **{event_type}**: {content}\n"

                            # Stream output content with header
                            elif content and event_type in ["task_completed", "task_output"]:
                                if not results_header_shown:
                                    yield "\n\n## 📊 Analysis Results\n\n"
                                    results_header_shown = True
                                yield f"{content}\n\n"

                            # Show progress indicator for events without content
                            elif not content:
                                yield "."

                            # Check for completion
                            if event_type == "crew_kickoff_completed":
                                # If there's completion content, show it
                                if content:
                                    if not results_header_shown:
                                        yield "\n\n## 📊 Analysis Results\n\n"
                                    yield f"{content}\n\n"

                                yield "\n✅ **Workflow completed successfully**\n"
                                return

                elif response.status_code >= 500:
                    # Server error - continue polling
                    logger.warning(f"Server error during polling: {response.status_code}")
                else:
                    # Client error - stop polling
                    yield f"\n\n❌ HTTP {response.status_code} error\n"
                    break

            except requests.exceptions.Timeout:
                logger.warning("Polling request timed out, continuing...")
            except Exception as e:
                logger.warning(f"Polling error: {str(e)}")

            # Sleep before next poll
            time.sleep(poll_interval)

    def pipe(self, body: dict, __files__: list = None) -> Union[str, Generator]:
        """
        Main pipeline entry point

        Args:
            body: Request body containing messages
            __files__: Optional list of uploaded files

        Returns:
            Generator yielding streaming response
        """
        def stream_workflow() -> Generator[str, None, None]:
            try:
                # Validate configuration
                is_valid, error_msg = self._validate_config()
                if not is_valid:
                    yield f"❌ **Configuration Error**: {error_msg}\n"
                    return

                # Extract user message
                messages = body.get("messages", [])
                if not messages:
                    yield "❌ No messages found in request.\n"
                    return

                user_message = messages[-1].get("content", "").strip()
                if not user_message:
                    yield "❌ Empty message. Please provide a query.\n"
                    return

                yield "# 📊 CSV Query Analyzer\n\n"

                # 3. Resolve and load file
                yield "🔄 Loading file..."
                try:
                    filename, file_bytes = self._resolve_file(body, __files__)
                    file_size_kb = len(file_bytes) / 1024
                    yield f" ✅ {filename} ({file_size_kb:.1f} KB)\n"
                except Exception as e:
                    yield f"\n❌ **File Error**: {str(e)}\n"
                    return

                # 4. Create session
                yield "🔄 Creating session..."
                try:
                    session_id = self._create_session()
                    yield f" ✅ {session_id[:8]}...\n"
                except Exception as e:
                    yield f"\n❌ **Session Error**: {str(e)}\n"
                    return

                # 5. Upload file
                yield "🔄 Uploading file..."
                try:
                    self._upload_file(session_id, filename, file_bytes)
                    yield f" ✅\n"
                except Exception as e:
                    yield f"\n❌ **Upload Error**: {str(e)}\n"
                    return

                # 6. Start workflow
                yield "🔄 Starting workflow..."
                try:
                    trace_id = self._kickoff_workflow(session_id, filename, user_message)
                    yield f" ✅ {trace_id[:8]}...\n"
                except Exception as e:
                    yield f"\n❌ **Kickoff Error**: {str(e)}\n"
                    return

                # 7. Stream events
                yield "\n🔍 **Analyzing your data**...\n"
                yield from self._poll_events(trace_id)

            except Exception as e:
                logger.error(f"Pipeline error: {str(e)}", exc_info=True)
                yield f"\n\n❌ **Critical Error**: {str(e)}\n"
                if self.valves.ENABLE_DEBUG_LOGGING:
                    import traceback
                    yield f"\n```\n{traceback.format_exc()}\n```\n"

        return stream_workflow()
