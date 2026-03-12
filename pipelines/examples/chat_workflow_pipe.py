"""
Chat Workflow Pipeline for Cloudera Agent Studio Integration

A conversational chat interface pipe that:
- Maintains session continuity across messages
- Sends user messages with full conversation context
- Streams responses in real-time
- Supports multi-turn conversations
"""

import requests
import time
import json
import logging
import hashlib
from pydantic import BaseModel, Field
from typing import Generator, Union, Optional, Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Pipe:
    """Chat Workflow Pipeline for Cloudera Agent Studio"""

    class Valves(BaseModel):
        """Configuration parameters"""
        WORKFLOW_ID: str = Field(
            default="",
            description="The ID of your Cloudera Workflow (required)",
        )
        MODEL_ENDPOINT: str = Field(
            default="",
            description="The base URL of your CML workflow (required)",
        )
        CDSW_APIV2_KEY: str = Field(
            default="",
            description="Your Cloudera API Key (required)"
        )

        # Timing configuration
        POLL_INTERVAL: int = Field(
            default=3,
            description="Initial seconds between polling events"
        )
        MAX_POLL_INTERVAL: int = Field(
            default=10,
            description="Maximum seconds between polls (for exponential backoff)"
        )
        OVERALL_TIMEOUT: int = Field(
            default=300,
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

        # Conversation settings
        MAX_CONTEXT_MESSAGES: int = Field(
            default=20,
            description="Maximum number of previous messages to include as context"
        )

        # Logging
        ENABLE_DEBUG_LOGGING: bool = Field(
            default=False,
            description="Enable detailed debug logging"
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "cloudera_chat_workflow"
        self.name = "Cloudera Chat Workflow"
        self.valves = self.Valves()
        # Session cache: maps conversation_id -> session_id
        self._session_cache: Dict[str, str] = {}

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
        """Execute HTTP request with retry logic and exponential backoff"""
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.valves.REQUEST_TIMEOUT

        for attempt in range(self.valves.MAX_RETRIES):
            try:
                if self.valves.ENABLE_DEBUG_LOGGING:
                    logger.debug(f"[Attempt {attempt + 1}] {description}: {url}")

                response = getattr(requests, method)(url, **kwargs)
                response.raise_for_status()
                return response

            except requests.exceptions.Timeout:
                if attempt == self.valves.MAX_RETRIES - 1:
                    raise Exception(f"{description} timed out after {self.valves.MAX_RETRIES} attempts")
                logger.warning(f"{description} timeout (attempt {attempt + 1}), retrying...")

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response else None
                if status_code and status_code < 500:
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

    def _get_conversation_id(self, body: dict) -> str:
        """Extract or generate a conversation ID from the request body"""
        # Try to get chat_id from body (Open WebUI passes this)
        chat_id = body.get("chat_id") or body.get("session_id") or body.get("id")
        if chat_id:
            return str(chat_id)

        # Fallback: generate ID from first message timestamp or content
        messages = body.get("messages", [])
        if messages:
            first_msg = messages[0]
            seed = f"{first_msg.get('content', '')}_{first_msg.get('timestamp', '')}"
            return hashlib.md5(seed.encode()).hexdigest()[:16]

        return "default"

    def _get_or_create_session(self, conversation_id: str) -> str:
        """Get existing session for conversation or create new one"""
        # Check if we have a cached session for this conversation
        if conversation_id in self._session_cache:
            cached_session = self._session_cache[conversation_id]
            logger.info(f"Reusing session {cached_session} for conversation {conversation_id}")
            return cached_session

        # Create new session
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

        # Cache the session for this conversation
        self._session_cache[conversation_id] = session_id
        logger.info(f"Created new session {session_id} for conversation {conversation_id}")
        return session_id

    def _kickoff_workflow(self, session_id: str, user_input: str, context: str = "[]") -> str:
        """Start the chat workflow execution"""
        payload = {
            "inputs": {
                "user_input": user_input,
                "context": context,
                "session_id": session_id,
            }
        }

        if self.valves.ENABLE_DEBUG_LOGGING:
            logger.debug(f"Kickoff payload: {json.dumps(payload, indent=2)}")

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
        seen_content = set()  # Track content we've already output to avoid duplicates
        poll_interval = self.valves.POLL_INTERVAL
        consecutive_empty_polls = 0

        while True:
            # Check overall timeout
            elapsed = time.time() - start_time
            if elapsed > self.valves.OVERALL_TIMEOUT:
                yield f"\n\n⏰ Timeout after {int(elapsed)}s\n"
                return

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
                        if consecutive_empty_polls > 3:
                            poll_interval = min(
                                poll_interval * 1.2,
                                self.valves.MAX_POLL_INTERVAL
                            )
                    else:
                        consecutive_empty_polls = 0
                        poll_interval = self.valves.POLL_INTERVAL

                    for event in events:
                        timestamp = event.get("timestamp")
                        if timestamp and timestamp not in seen_timestamps:
                            seen_timestamps.add(timestamp)

                            event_type = event.get("type")
                            content = (
                                event.get("response") or
                                event.get("output") or
                                event.get("outout") or  # Handle typo in API
                                ""
                            )

                            # Check for failure events
                            if event_type in ["crew_kickoff_failed", "workflow_failed", "error"]:
                                error_msg = event.get("error", "Unknown error")
                                yield f"\n\n❌ **Error**: {error_msg}\n"

                                if "metadata" in event:
                                    metadata = event.get("metadata")
                                    if isinstance(metadata, dict) and "error" in metadata:
                                        yield f"```\n{metadata['error']}\n```\n"

                                logger.error(f"Workflow failed: {event_type} - {error_msg}")
                                return

                            # Stream output content directly (avoid duplicates)
                            if content and event_type in ["task_completed", "task_output", "crew_kickoff_completed"]:
                                # Use hash to detect duplicate content
                                content_hash = hash(content)
                                if content_hash not in seen_content:
                                    seen_content.add(content_hash)
                                    yield f"{content}"

                            # Check for completion
                            if event_type == "crew_kickoff_completed":
                                return

                elif response.status_code >= 500:
                    logger.warning(f"Server error during polling: {response.status_code}")
                else:
                    yield f"\n\n❌ HTTP {response.status_code} error\n"
                    return

            except requests.exceptions.Timeout:
                logger.warning("Polling request timed out, continuing...")
            except Exception as e:
                logger.warning(f"Polling error: {str(e)}")

            time.sleep(poll_interval)

    def _build_context(self, messages: List[Dict]) -> str:
        """Build context from full conversation history"""
        context = []
        # Include all previous messages as context (excluding the current user message)
        max_context = self.valves.MAX_CONTEXT_MESSAGES
        history_messages = messages[:-1][-max_context:] if len(messages) > 1 else []

        for msg in history_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                context.append({"role": role, "content": content})

        if self.valves.ENABLE_DEBUG_LOGGING:
            logger.debug(f"Built context with {len(context)} messages")

        return json.dumps(context)

    def pipe(self, body: dict, __files__: list = None) -> Union[str, Generator]:
        """Main pipeline entry point"""
        def stream_workflow() -> Generator[str, None, None]:
            try:
                # Validate configuration
                is_valid, error_msg = self._validate_config()
                if not is_valid:
                    yield f"❌ **Configuration Error**: {error_msg}\n"
                    yield "Please configure WORKFLOW_ID, MODEL_ENDPOINT, and CDSW_APIV2_KEY in the pipe settings.\n"
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

                # Get conversation ID for session management
                conversation_id = self._get_conversation_id(body)

                # Build context from full conversation history
                context = self._build_context(messages)

                if self.valves.ENABLE_DEBUG_LOGGING:
                    logger.debug(f"Conversation ID: {conversation_id}")
                    logger.debug(f"User message: {user_message}")
                    logger.debug(f"Context: {context}")

                # Get or create session for this conversation
                try:
                    session_id = self._get_or_create_session(conversation_id)
                except Exception as e:
                    yield f"❌ **Connection Error**: {str(e)}\n"
                    return

                # Start workflow with user message and conversation context
                try:
                    trace_id = self._kickoff_workflow(session_id, user_message, context)
                except Exception as e:
                    yield f"❌ **Error**: {str(e)}\n"
                    return

                # Stream events - this is where the response comes from
                yield from self._poll_events(trace_id)

            except Exception as e:
                logger.error(f"Pipeline error: {str(e)}", exc_info=True)
                yield f"❌ **Critical Error**: {str(e)}\n"
                if self.valves.ENABLE_DEBUG_LOGGING:
                    import traceback
                    yield f"```\n{traceback.format_exc()}\n```\n"

        return stream_workflow()
