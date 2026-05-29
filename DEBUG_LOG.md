# Debug & Improvements - Admin Server & Panel

## Changes Made

### 1. **admin_server.py - Better File Discovery & Logging**

#### New Helper Function:
- Added `find_file_path(filename: str)` to automatically find actual file path
  - Searches Data directory recursively  
  - Tries both .pdf and .docx extensions
  - Returns full Path or None if not found
  - Logs each step for debugging

#### Improved Logging in `/process/file` endpoint:
- Logs file path discovery process
- Logs actual doc_id being processed
- Catches and logs exceptions with full traceback
- Shows whether file exists before processing

#### Enhanced Retry Logic:
- Added traceback.print_exc() for detailed error output
- Logs attempt number and backoff timing
- Truncates long error messages (500 char limit)
- Shows detailed retry info

### 2. **admin.html - Loading Indicators**

#### Visual Feedback During Processing:
- Files with status "processing" now show animated loading spinner
- Spinner appears next to status text (⚙️ Đang xử lý)
- Uses existing CSS animation `@keyframes spin`
- Spinner properly vertical-aligned

#### Implementation:
- Modified `renderFileRow()` to detect processing status
- Builds special HTML with inline spinner when `status === 'processing'`
- CSS: `vertical-align: middle` ensures proper alignment

---

## How to Debug

### When You See "File Not Found" Error:

1. **Check Server Logs** - Look for these patterns:
```
[DEBUG] find_file_path: searching for 'FILENAME'
[DEBUG] find_file_path: found at /path/to/file.pdf
[WARNING] find_file_path: file 'FILENAME' not found in Data directory
```

2. **Check Background Processing** - Look for:
```
[API] POST /process/file - request.path=...
[API] Found file: /path/to/file...
[PROCESS] Starting processing for FILENAME...
[ATTEMPT 1] Processing FILENAME...
```

3. **Full Error Stack** - If processing fails:
```
[ATTEMPT N] FILENAME failed: ERROR_MESSAGE
Traceback (most recent call last):
  File "...", line X, in ...
  ...
[FAILED] FILENAME after N attempts
```

### Common Issues:

| Issue | What to Check | Log Pattern |
|-------|---------------|------------|
| File not found | Does file exist in Data/? | `find_file_path: file 'X' not found` |
| Process fails | Check unified_pipeline.py | `[FAILED] ... after N attempts` |
| Rate limit | API quota hit | `429 or 503 in error` |
| Path mismatch | Filename vs actual name | Compare discover_files() output with actual files |

---

## Testing

To manually test processing:

1. Start server: `python admin_server.py`
2. Open admin panel in browser
3. Click process button on a file
4. Watch terminal for detailed logs
5. File status badge will show loading spinner while processing

---

## File Structure for Processing

Files are discovered and processed as:
- **Original files**: `Data/{category}/{filename}.pdf` or `.docx`
- **Partitioned files**: Part files have chunks embedded in database with names like `filename_01`, `filename_02`
- **Tracking**: Pipeline log tracks both parent and part file entries
