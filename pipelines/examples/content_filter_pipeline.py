"""
Content Filter Pipeline for Open WebUI
Demonstrates content filtering, keyword detection, and response modification
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import re


class Pipeline:
    """
    Content filter pipeline that:
    - Filters inappropriate content
    - Detects keywords
    - Adds warnings or modifications based on content
    """

    class Valves(BaseModel):
        """Pipeline configuration"""
        priority: int = Field(default=0, description="Execution priority")
        enabled: bool = Field(default=True, description="Enable/disable pipeline")

        # Content filtering settings
        block_inappropriate: bool = Field(
            default=True,
            description="Block messages containing inappropriate keywords"
        )
        blocked_keywords: str = Field(
            default="spam,offensive,inappropriate",
            description="Comma-separated list of blocked keywords"
        )

        # Warning settings
        add_warnings: bool = Field(
            default=True,
            description="Add warnings for sensitive topics"
        )
        sensitive_topics: str = Field(
            default="medical,legal,financial",
            description="Comma-separated list of sensitive topics"
        )

        # Response modification
        max_tokens: int = Field(
            default=2000,
            description="Maximum tokens for model responses"
        )
        temperature_override: float = Field(
            default=0.7,
            description="Override temperature setting (0.0 to 2.0)"
        )

    def __init__(self):
        self.type = "filter"
        self.id = "content_filter"
        self.name = "Content Filter Pipeline"
        self.valves = self.Valves()
        self.pipelines = ["*"]  # Apply to all models

    async def on_startup(self):
        print(f"Starting {self.name}")
        print(f"Blocked keywords: {self.valves.blocked_keywords}")

    async def on_shutdown(self):
        print(f"Shutting down {self.name}")

    def _get_keyword_list(self, keyword_string: str) -> List[str]:
        """Parse comma-separated keywords into list"""
        return [k.strip().lower() for k in keyword_string.split(",") if k.strip()]

    def _contains_blocked_content(self, text: str) -> tuple[bool, Optional[str]]:
        """Check if text contains blocked keywords"""
        if not self.valves.block_inappropriate:
            return False, None

        blocked = self._get_keyword_list(self.valves.blocked_keywords)
        text_lower = text.lower()

        for keyword in blocked:
            if keyword in text_lower:
                return True, keyword
        return False, None

    def _detect_sensitive_topic(self, text: str) -> Optional[str]:
        """Detect if text contains sensitive topics"""
        if not self.valves.add_warnings:
            return None

        topics = self._get_keyword_list(self.valves.sensitive_topics)
        text_lower = text.lower()

        for topic in topics:
            if topic in text_lower:
                return topic
        return None

    async def inlet(self, body: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process incoming request"""
        if not self.valves.enabled:
            return body

        print(f"[Content Filter] Processing request from {user.get('name', 'Unknown')}")

        # Check all user messages for blocked content
        if "messages" in body:
            for message in body["messages"]:
                if message.get("role") == "user":
                    content = message.get("content", "")

                    # Check for blocked content
                    is_blocked, keyword = self._contains_blocked_content(content)
                    if is_blocked:
                        raise Exception(
                            f"Content blocked: Message contains inappropriate keyword '{keyword}'. "
                            f"Please rephrase your message."
                        )

                    # Check for sensitive topics and add warning
                    sensitive_topic = self._detect_sensitive_topic(content)
                    if sensitive_topic:
                        warning = (
                            f"\n\n⚠️ Note: This query involves {sensitive_topic} topics. "
                            f"Please consult with qualified professionals for important decisions."
                        )
                        message["content"] = content + warning

        # Override model parameters
        if "max_tokens" not in body or body["max_tokens"] > self.valves.max_tokens:
            body["max_tokens"] = self.valves.max_tokens

        if "temperature" in body:
            body["temperature"] = self.valves.temperature_override

        return body

    async def outlet(self, body: Dict[str, Any], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process outgoing response"""
        if not self.valves.enabled:
            return body

        print(f"[Content Filter] Processing response for {user.get('name', 'Unknown')}")

        # Add disclaimer to responses
        if "messages" in body and len(body["messages"]) > 0:
            last_message = body["messages"][-1]
            if last_message.get("role") == "assistant":
                content = last_message.get("content", "")

                # Check if response discusses sensitive topics
                for message in body["messages"]:
                    if message.get("role") == "user":
                        topic = self._detect_sensitive_topic(message.get("content", ""))
                        if topic:
                            disclaimer = (
                                f"\n\n---\n"
                                f"*Disclaimer: This information is for general purposes only. "
                                f"For {topic} matters, please consult qualified professionals.*"
                            )
                            last_message["content"] = content + disclaimer
                            break

        return body
