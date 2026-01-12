# Open WebUI Pipelines

This directory contains custom pipelines for Open WebUI, including examples and templates for creating your own.

## Directory Structure

```
pipelines/
├── README.md                           # This file
├── examples/                           # Example pipelines for learning
│   ├── sample_pipeline.py             # Basic pipeline template
│   └── content_filter_pipeline.py     # Advanced content filter example
└── custom/                            # Your custom pipelines go here
```

**Organization:**
- `examples/` - Reference implementations and learning templates (do not modify)
- `custom/` - Place your production pipelines here (git-ignored by default)

## What are Pipelines?

Pipelines are Python plugins that allow you to:
- Pre-process requests before they reach the AI model (inlet filter)
- Post-process responses after the model generates them (outlet filter)
- Configure behavior through "valves" (adjustable parameters)
- Add custom logic, validation, logging, and more

## Sample Pipelines Included

### 1. `examples/sample_pipeline.py` - Basic Pipeline Template
A simple demonstration showing:
- ✅ Basic inlet/outlet filter structure
- ✅ Configurable valves (parameters)
- ✅ Message modification
- ✅ Logging capabilities
- ✅ Lifecycle hooks (startup/shutdown)

**Features:**
- Adds prefixes to user messages
- Truncates long messages
- Adds timestamps
- Logs all requests

### 2. `examples/content_filter_pipeline.py` - Content Filtering
A more advanced example showing:
- ✅ Keyword blocking
- ✅ Sensitive topic detection
- ✅ Content warnings
- ✅ Response disclaimers
- ✅ Parameter overrides (temperature, max_tokens)

**Features:**
- Blocks inappropriate content
- Detects medical/legal/financial topics
- Adds warnings and disclaimers
- Controls model parameters

## How to Install a Pipeline

### Method 1: Upload via UI (Recommended)

1. Open Open WebUI
2. Go to **Admin Settings** → **Pipelines**
3. Select your pipeline server URL
4. Click **"Upload Pipeline"**
5. Select the `.py` file from `pipelines/examples/` or `pipelines/custom/`
6. Click upload

### Method 2: Install from GitHub

If you host your pipeline on GitHub:

1. Push your `.py` file to a GitHub repository
2. Get the raw URL (e.g., `https://raw.githubusercontent.com/user/repo/main/pipeline.py`)
3. Go to **Admin Settings** → **Pipelines**
4. Paste the URL in **"Install from Github URL"**
5. Click download

## Configuring Pipeline Valves

After uploading, configure the pipeline:

1. Go to **Admin Settings** → **Pipelines**
2. Select your pipeline from the dropdown
3. Adjust the valve values:
   - Toggle switches for boolean values
   - Text inputs for strings/numbers
   - Dropdowns for enum options
4. Click **Save**

## Pipeline Structure

```python
class Pipeline:
    class Valves(BaseModel):
        # Configuration parameters
        enabled: bool = Field(default=True)
        # Add more fields...

    def __init__(self):
        self.type = "filter"  # or "pipe"
        self.id = "unique_id"
        self.name = "Display Name"
        self.valves = self.Valves()

    async def inlet(self, body, user):
        # Pre-process request
        return body

    async def outlet(self, body, user):
        # Post-process response
        return body
```

## Key Components

### Valves (Configuration)
```python
class Valves(BaseModel):
    priority: int = Field(default=0)
    enabled: bool = Field(default=True)
    custom_param: str = Field(default="value")
```

### Inlet Filter (Request Processing)
```python
async def inlet(self, body: Dict, user: Dict) -> Dict:
    # Modify body["messages"]
    # Add/remove/edit messages
    # Validate input
    # Raise exceptions to block requests
    return body
```

### Outlet Filter (Response Processing)
```python
async def outlet(self, body: Dict, user: Dict) -> Dict:
    # Modify response
    # Add disclaimers
    # Format output
    return body
```

## Common Use Cases

### 1. Message Prefix/Suffix
```python
message["content"] = f"{prefix} {message['content']} {suffix}"
```

### 2. Content Validation
```python
if contains_inappropriate(content):
    raise Exception("Content blocked")
```

### 3. Add System Context
```python
body["messages"].insert(0, {
    "role": "system",
    "content": "Additional instructions..."
})
```

### 4. Modify Model Parameters
```python
body["temperature"] = 0.5
body["max_tokens"] = 1000
```

### 5. Add Response Disclaimers
```python
last_message["content"] += "\n\n*Disclaimer: ...*"
```

## Debugging Tips

1. **Check Logs**: Pipeline print statements appear in backend logs
2. **Use Try-Except**: Wrap logic in try-except to prevent crashes
3. **Test Valves**: Start with default values, adjust gradually
4. **Raise Exceptions**: Use exceptions to block requests with clear messages

## Security Considerations

⚠️ **Warning**: Pipelines have arbitrary code execution capabilities

- Only install pipelines from trusted sources
- Review code before uploading
- Test in development environment first
- Use valve-based enable/disable switches
- Monitor logs for unexpected behavior

## Maintenance Best Practices

1. **Version Control**: Keep pipeline code in git
2. **Document Changes**: Comment your modifications
3. **Test Before Deploy**: Validate in staging
4. **Monitor Performance**: Check for slowdowns
5. **Update Regularly**: Keep dependencies current
6. **Backup Configs**: Export valve settings

## Advanced Features

### Priority System
```python
self.valves.priority = 0  # Lower numbers execute first
```

### Target Specific Models
```python
self.pipelines = ["gpt-4", "claude-3"]  # Only these models
# or
self.pipelines = ["*"]  # All models
```

### Async Operations
```python
import aiohttp

async def inlet(self, body, user):
    async with aiohttp.ClientSession() as session:
        result = await session.get("https://api.example.com")
    # Use result...
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Pipeline not appearing | Check if pipeline server is running |
| Changes not taking effect | Re-upload pipeline or restart server |
| Errors in console | Check backend logs for details |
| Valves not saving | Ensure proper Field() definitions |
| Performance slow | Optimize async operations |

## Resources

- [Open WebUI Documentation](https://docs.openwebui.com)
- [Pydantic Documentation](https://docs.pydantic.dev) (for Valves)
- [FastAPI Documentation](https://fastapi.tiangolo.com) (pipeline framework)

## Example Modifications

### Add Rate Limiting
```python
class Valves(BaseModel):
    max_requests_per_minute: int = Field(default=10)

# Track requests in inlet filter
```

### Log to External Service
```python
import aiohttp

async def inlet(self, body, user):
    async with aiohttp.ClientSession() as session:
        await session.post(
            "https://logging-service.com/log",
            json={"user": user, "timestamp": time.time()}
        )
```

### Translate Messages
```python
async def inlet(self, body, user):
    for message in body["messages"]:
        if message["role"] == "user":
            # Call translation API
            translated = await translate(message["content"])
            message["content"] = translated
```

## Contributing

Feel free to create your own pipelines and share them with the community!
