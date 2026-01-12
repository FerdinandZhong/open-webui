"""
Sample Pipeline for Open WebUI
This is a demonstration pipeline showing inlet/outlet filters and valves configuration.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import time


class Pipeline:
    """
    A sample pipeline that demonstrates:
    - Inlet filter (pre-processing requests before they reach the model)
    - Outlet filter (post-processing responses from the model)
    - Valves (configurable parameters)
    """

    class Valves(BaseModel):
        """
        Configuration parameters for the pipeline
        These can be modified through the UI without changing code
        """
        priority: int = Field(
            default=0,
            description="Pipeline execution priority (lower numbers run first)"
        )
        enabled: bool = Field(
            default=True,
            description="Enable or disable this pipeline"
        )
        prefix_text: str = Field(
            default="[Pipeline]",
            description="Text to prepend to user messages"
        )
        max_message_length: int = Field(
            default=1000,
            description="Maximum length for messages (characters)"
        )
        log_requests: bool = Field(
            default=True,
            description="Log all requests passing through this pipeline"
        )

    def __init__(self):
        """Initialize the pipeline with default valve values"""
        self.type = "filter"  # Can be "filter" or "pipe"
        self.id = "sample_pipeline"
        self.name = "Sample Pipeline"
        self.valves = self.Valves()

    async def on_startup(self):
        """
        Called when the pipeline starts
        Use for initialization, loading models, connecting to databases, etc.
        """
        print(f"Pipeline '{self.name}' started successfully")

    async def on_shutdown(self):
        """
        Called when the pipeline shuts down
        Use for cleanup, closing connections, etc.
        """
        print(f"Pipeline '{self.name}' shutting down")

    async def inlet(self, body: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Inlet filter: Process request BEFORE it reaches the model

        Args:
            body: The request payload containing messages, model, etc.
            user: User information (id, email, name, role)

        Returns:
            Modified body dictionary
        """
        if not self.valves.enabled:
            return body

        # Log the request
        if self.valves.log_requests:
            print(f"[INLET] User: {user.get('name', 'Unknown')} | Model: {body.get('model', 'Unknown')}")
            print(f"[INLET] Message count: {len(body.get('messages', []))}")

        # Add timestamp to system context
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        # Modify messages
        if "messages" in body:
            for message in body["messages"]:
                # Add prefix to user messages
                if message.get("role") == "user":
                    original_content = message.get("content", "")

                    # Truncate if too long
                    if len(original_content) > self.valves.max_message_length:
                        original_content = original_content[:self.valves.max_message_length] + "..."

                    message["content"] = f"{self.valves.prefix_text} {original_content}"

            # Add system message with timestamp
            body["messages"].insert(0, {
                "role": "system",
                "content": f"Current timestamp: {current_time}"
            })

        return body

    async def outlet(self, body: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Outlet filter: Process response AFTER it comes from the model

        Args:
            body: The response payload
            user: User information

        Returns:
            Modified body dictionary
        """
        if not self.valves.enabled:
            return body

        # Log the response
        if self.valves.log_requests:
            print(f"[OUTLET] Response processed for user: {user.get('name', 'Unknown')}")

        # You can modify the response here
        # For example, add a footer to all responses
        if "messages" in body and len(body["messages"]) > 0:
            last_message = body["messages"][-1]
            if last_message.get("role") == "assistant":
                original_content = last_message.get("content", "")
                last_message["content"] = f"{original_content}\n\n---\n*Processed by {self.name}*"

        return body
