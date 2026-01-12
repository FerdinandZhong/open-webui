# CSV Query Analyzer - Optimization Guide

This document details the optimizations made to `csv_query_analyzer.py`.

## Files

- **Original:** `examples/csv_query_analyzer.py`
- **Optimized:** `examples/csv_query_analyzer_optimized.py`

## Key Improvements

### 1. Dynamic File Handling ✅

**Before:**
```python
# Hardcoded file path
file_path = "/home/cdsw/backend/data/uploads/3f39cc13-5973-4039-be5b-afc55b8f70c1_temperature_data_small.csv"
filename = "temperature_data_small.csv"
```

**After:**
```python
def _resolve_file(self, body: dict, __files__: list = None):
    # 1. Try Open WebUI file uploads
    # 2. Extract from message content
    # 3. Search default upload directory
    # Returns: (filename, file_bytes)
```

**Benefits:**
- Supports file uploads through Open WebUI interface
- Automatically finds most recent CSV in upload directory
- Validates file extension and size
- Works with multiple file sources

---

### 2. Retry Logic with Exponential Backoff ✅

**Before:**
```python
# No retry logic - single attempt only
response = requests.post(url, ...)
response.raise_for_status()
```

**After:**
```python
def _retry_request(self, method, url, description, **kwargs):
    for attempt in range(self.valves.MAX_RETRIES):
        try:
            response = getattr(requests, method)(url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            # Exponential backoff between retries
            sleep_time = (self.valves.RETRY_BACKOFF ** attempt)
            time.sleep(sleep_time)
```

**Benefits:**
- Handles transient network failures automatically
- Configurable retry attempts (default: 3)
- Exponential backoff prevents API overload
- Different handling for client vs server errors

---

### 3. Better Error Handling ✅

**Before:**
```python
except Exception as e:
    yield f"\n❌ **Critical Error:** {str(e)}"
```

**After:**
```python
# Specific error handling at each stage:
try:
    filename, file_bytes = self._resolve_file(body, __files__)
except Exception as e:
    yield f"❌ **File Error:** {str(e)}\n"
    return  # Stop execution early

# Plus logging
logger.error(f"Pipeline error: {str(e)}", exc_info=True)
```

**Benefits:**
- Specific error messages for each failure point
- Early termination on critical errors
- Detailed logging for debugging
- User-friendly error messages

---

### 4. Configuration Validation ✅

**Before:**
```python
# No validation - fails during execution
headers_cml = {
    "Authorization": f"Bearer {self.valves.CDSW_APIV2_KEY}",
}
```

**After:**
```python
def _validate_config(self) -> tuple[bool, Optional[str]]:
    if not self.valves.CDSW_APIV2_KEY:
        return False, "API Key (CDSW_APIV2_KEY) is required"
    # ... more validation
    return True, None

# Called before execution
is_valid, error_msg = self._validate_config()
if not is_valid:
    yield f"❌ **Configuration Error:** {error_msg}"
    return
```

**Benefits:**
- Fails fast with clear error messages
- Prevents wasted API calls
- Guides user to fix configuration
- Validates all required settings

---

### 5. Improved Polling Strategy ✅

**Before:**
```python
# Fixed polling interval
while True:
    response = requests.get(...)
    time.sleep(self.valves.POLL_INTERVAL)  # Always 5 seconds
```

**After:**
```python
# Adaptive polling with exponential backoff
poll_interval = self.valves.POLL_INTERVAL
consecutive_empty_polls = 0

if not events:
    consecutive_empty_polls += 1
    if consecutive_empty_polls > 2:
        # Increase interval for empty polls
        poll_interval = min(
            poll_interval * 1.2,
            self.valves.MAX_POLL_INTERVAL
        )
else:
    poll_interval = self.valves.POLL_INTERVAL  # Reset
```

**Benefits:**
- Reduces unnecessary API calls when idle
- Faster response when events are streaming
- Configurable min/max intervals
- Lower server load

---

### 6. Code Organization ✅

**Before:**
```python
def pipe(self, body: dict, __files__: list = None):
    def stream_workflow():
        # All 150+ lines of logic here
        # File handling, session creation, upload, polling...
```

**After:**
```python
# Separated concerns into focused methods:
def _validate_config(self)
def _resolve_file(self, body, __files__)
def _load_file(self, file_path, filename)
def _create_session(self)
def _upload_file(self, session_id, filename, file_bytes)
def _kickoff_workflow(self, session_id, filename, user_message)
def _poll_events(self, trace_id)
def _retry_request(self, method, url, description, **kwargs)
```

**Benefits:**
- Each function has single responsibility
- Easier to test and debug
- Better code reusability
- Clearer logic flow

---

### 7. Enhanced Configuration ✅

**New Valves Added:**
```python
# Retry configuration
MAX_RETRIES: int = 3
RETRY_BACKOFF: float = 1.5

# Performance tuning
MAX_POLL_INTERVAL: int = 15
REQUEST_TIMEOUT: int = 30

# File handling
MAX_FILE_SIZE_MB: int = 50
ALLOWED_EXTENSIONS: str = ".csv,.tsv,.txt"
DEFAULT_UPLOAD_DIR: str = "/home/cdsw/backend/data/uploads"

# Debugging
ENABLE_DEBUG_LOGGING: bool = False
```

**Benefits:**
- Fine-tune behavior without code changes
- Per-deployment customization
- Better control over timeouts
- Easy to enable debug mode

---

### 8. Logging & Debugging ✅

**Before:**
```python
# No logging - silent failures
except Exception:
    pass  # Silently retry
```

**After:**
```python
import logging
logger = logging.getLogger(__name__)

# Informational logging
logger.info(f"Loaded file: {filename} ({file_size_mb:.2f}MB)")
logger.info(f"Created session: {session_id}")

# Warning logging
logger.warning(f"Server error during polling: {response.status_code}")

# Error logging with full traceback
logger.error(f"Pipeline error: {str(e)}", exc_info=True)
```

**Benefits:**
- Track pipeline execution in logs
- Identify issues quickly
- Debug production problems
- Monitor performance

---

### 9. Resource Management ✅

**Before:**
```python
# File read entirely into memory
with open(file_path, "rb") as f:
    file_bytes = f.read()
```

**After:**
```python
# Validation before reading
file_size_mb = path.stat().st_size / (1024 * 1024)
if file_size_mb > self.valves.MAX_FILE_SIZE_MB:
    raise Exception(f"File size ({file_size_mb:.1f}MB) exceeds limit")

# Then read with validation
with open(file_path, "rb") as f:
    file_bytes = f.read()
```

**Benefits:**
- Prevents memory exhaustion
- Validates file size before processing
- Configurable size limits
- Better error messages

---

### 10. Bug Fixes ✅

**Typo Fixed:**
```python
# Line 139 - typo
elif "outout" in event:  # Wrong spelling
    yield f"\n{event['outout']}\n"

# Still handled for backward compatibility
content = (
    event.get("response") or
    event.get("output") or
    event.get("outout") or  # Handle API typo
    ""
)
```

---

## Performance Comparison

| Metric | Original | Optimized | Improvement |
|--------|----------|-----------|-------------|
| **API Calls (idle)** | ~12/min | ~4/min | 67% reduction |
| **Error Recovery** | ❌ None | ✅ 3 retries | 3x resilience |
| **Config Validation** | ❌ Runtime | ✅ Upfront | Faster failure |
| **File Handling** | ❌ Hardcoded | ✅ Dynamic | Flexible |
| **Code Lines** | 156 | 464 | Better structure |
| **Logging** | ❌ None | ✅ Full | Observable |
| **Memory Safety** | ❌ None | ✅ Validated | Safer |

---

## Migration Guide

### For Existing Users

1. **Backup your configuration:**
   ```python
   # Save your current valve values
   WORKFLOW_ID = "db40e298-..."
   MODEL_ENDPOINT = "https://workflow-..."
   CDSW_APIV2_KEY = "your-key"
   ```

2. **Upload optimized version:**
   - Go to Admin Settings → Pipelines
   - Upload `csv_query_analyzer_optimized.py`
   - Enter your saved valve values

3. **Configure new settings:**
   - `MAX_RETRIES`: Start with 3 (recommended)
   - `MAX_FILE_SIZE_MB`: Set based on your files
   - `ALLOWED_EXTENSIONS`: Add `.tsv` if needed
   - `ENABLE_DEBUG_LOGGING`: Enable for first tests

4. **Test with a small file:**
   - Upload a test CSV
   - Run a simple query
   - Check logs for any issues

### Using File Uploads

**Method 1 - Open WebUI Upload:**
1. Click the attachment icon in chat
2. Upload your CSV file
3. Type your query
4. Send

**Method 2 - File Path in Message:**
```
Analyze this file: /path/to/data.csv

What are the top 10 values?
```

**Method 3 - Auto-detect (fallback):**
- Just place CSV in upload directory
- Pipeline finds most recent file
- Type your query

---

## Troubleshooting

### Issue: "Configuration Error: API Key is required"
**Solution:** Set `CDSW_APIV2_KEY` in pipeline valves

### Issue: "File Error: No CSV file found"
**Solution:**
- Upload file before sending message
- Or provide file path in message
- Or check `DEFAULT_UPLOAD_DIR` setting

### Issue: "Timeout: Workflow exceeded 120s"
**Solution:** Increase `OVERALL_TIMEOUT` valve

### Issue: Slow polling
**Solution:**
- Decrease `POLL_INTERVAL` for faster response
- Increase `MAX_POLL_INTERVAL` to reduce API calls

### Issue: Network errors
**Solution:**
- Increase `MAX_RETRIES` to 5
- Increase `REQUEST_TIMEOUT` to 60

### Debug Mode
Enable detailed logging:
```python
ENABLE_DEBUG_LOGGING = True
```

Check backend logs for detailed execution trace.

---

## Best Practices

1. **Start Conservative:**
   - Use default valve values initially
   - Tune based on actual performance

2. **Monitor Logs:**
   - Enable debug logging for first week
   - Review for any warnings/errors
   - Adjust timeouts as needed

3. **File Size Limits:**
   - Set realistic `MAX_FILE_SIZE_MB`
   - Consider your server memory
   - Test with maximum expected size

4. **Network Resilience:**
   - Keep `MAX_RETRIES` at 3 or higher
   - Use higher values for unstable networks
   - Monitor retry rates in logs

5. **Polling Efficiency:**
   - Balance responsiveness vs API calls
   - Use adaptive polling (default)
   - Increase `MAX_POLL_INTERVAL` for long jobs

---

## Future Enhancements

Potential improvements for future versions:

- [ ] Concurrent file uploads
- [ ] Streaming file processing
- [ ] Progress percentage indicators
- [ ] Session cleanup/cancellation
- [ ] Multiple file support
- [ ] CSV preview in chat
- [ ] Result caching
- [ ] Webhook notifications
- [ ] Custom event handlers

---

## Support

For issues or questions:
1. Check logs with `ENABLE_DEBUG_LOGGING=True`
2. Review valve configuration
3. Test with simple query first
4. Check Cloudera API documentation
