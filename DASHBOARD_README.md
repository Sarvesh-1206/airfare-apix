# APIx Streamlit Dashboard

## Overview

This is the Streamlit frontend dashboard for the India Real-Time Airfare Price Index (APIx). The dashboard is a presentation layer that consumes the FastAPI backend and displays APIx data through an institutional, professional interface.

## Quick Start

### Prerequisites

- Python 3.8+
- Installed dependencies (see requirements.txt)
- FastAPI backend running on http://127.0.0.1:8000

### Installation

```bash
pip install -r requirements.txt
```

### Running the Dashboard

1. **Start the FastAPI backend:**

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

2. **In a separate terminal, start the Streamlit dashboard:**

```bash
streamlit run src/dashboard/app.py
```

The dashboard will be available at `http://localhost:8501`

### Environment Variables

- `APIX_API_URL` — Backend API URL (default: `http://127.0.0.1:8000`)

Example:
```bash
set APIX_API_URL=http://your-api-host:8000
streamlit run src/dashboard/app.py
```

## Dashboard Pages

### 1. Overview
Executive monitoring dashboard displaying:
- Five KPI cards (APIx, Daily Change, Cumulative Change, Observations, Routes)
- APIx Index Trend chart with time series visualization
- Route Performance panel showing DGCA weights
- Data Quality Summary
- APIx Dataset metadata

### 2. Route Analysis
Detailed analysis of individual routes:
- Route weight distribution chart
- Route index values comparison
- Detailed route metrics table

### 3. Lead-Time Analysis
Lead-time and fare-class stratified analysis:
- Fare class selector (Economy/Business)
- Lead-time index trend chart
- Lead-time metrics by advance-purchase days (T+1, T+7, T+15, T+30, T+45)

### 4. Historical Index
Time-series view of the complete APIx history:
- Line chart showing APIx movement over time
- Daily summary statistics table
- Collection date filtering

### 5. Data Quality
Quality control report displaying:
- Overall QC status (PASS/REVIEW/FAIL)
- Individual QC check results
- Pass/Review/Fail counts
- Detailed check messages and thresholds

### 6. Methodology
Educational content explaining:
- APIx calculation methodology
- Index base and weighting approach
- Lead-time buckets and fare classes
- Routes included in the index
- Clarification that ML is NOT used in APIx calculation

### 7. API / Data Access
Developer documentation:
- API endpoint list
- API status indicator
- Base URL configuration
- Links to Swagger documentation

## Architecture

```
src/dashboard/
├── __init__.py
├── api_client.py      # API client layer
└── app.py             # Main Streamlit application
```

### API Client (`api_client.py`)

Clean API client handling:
- HTTP connection management
- Retry strategy for failed requests
- Error handling with user-friendly messages
- Request timeout configuration

Provides methods:
- `health()` — Check backend availability
- `latest_index()` — Get current APIx value
- `index_history()` — Get time series data
- `route_indices()` — Get route-level data
- `lead_time_indices()` — Get lead-time data
- `quality_report()` — Get QC report
- `summary()` — Get metadata

### Main Application (`app.py`)

Features:
- Responsive layout optimized for desktop, tablet, and mobile
- Professional color scheme (white backgrounds, navy/blue accents)
- Status indicators (green/amber/red)
- 30-second cache for API responses
- Graceful error handling
- Sidebar navigation
- Refresh functionality

## Data Handling

**Important:** The dashboard does NOT:
- Perform any APIx index calculations
- Load raw data files
- Duplicate backend logic
- Use ML models for APIx calculation

The dashboard ONLY:
- Displays data from FastAPI backend
- Formats data for presentation
- Caches responses (30 seconds)
- Handles errors gracefully

## Caching

Streamlit caching configuration:
- Cache TTL: 30 seconds
- Cache cleared on manual refresh
- Automatic refresh on navigation changes

## Error Handling

The dashboard gracefully handles:
- Backend unavailable
- Network timeouts
- Malformed JSON responses
- Missing data fields
- Empty responses

Each page remains functional even if one endpoint fails.

## Testing

Run the API client test:
```bash
python test_api_client.py
```

Expected output:
```
✓ Health check: healthy
✓ Latest index: APIx=100.0, Date=2026-09-01, Routes=6
✓ Index history: 1 records
✓ Route indices: 6 routes
✓ Lead-time indices (Economy): 5 records
✓ Quality report: Status=REVIEW, 9 PASS, 2 REVIEW, 0 FAIL
✓ Summary: 1 collection days, base index=100.0, 6 routes
```

## Known Limitations

### Single Collection Day
When only one collection day exists:
- Index trend chart shows "Building time series" message
- Lead-time analysis shows base-period values
- Historical index shows single-day statistics
- No trend movement is displayed to avoid false implications

This is intentional and correct behavior.

## Browser Compatibility

Tested and supported on:
- Chrome/Chromium (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

Mobile viewing is supported with responsive layout.

## Performance

- Page load time: ~1-2 seconds
- Chart rendering: <500ms
- API response caching: 30 seconds
- Backend API response time: ~100-200ms

## Troubleshooting

### Dashboard won't start
- Verify Python and dependencies: `pip install -r requirements.txt`
- Check Streamlit is installed: `streamlit --version`

### "API Unavailable" error
- Verify FastAPI backend is running: `curl http://127.0.0.1:8000/health`
- Check `APIX_API_URL` environment variable
- Verify firewall allows connection to port 8000

### Data not updating
- Click the refresh button in the sidebar
- Clear browser cache (Ctrl+Shift+Delete)
- Check backend is generating new data

### Charts not rendering
- Verify Plotly is installed: `pip list | grep plotly`
- Try refreshing the page

## Development

### Adding a new page

1. Create render function in `app.py`:
```python
def render_my_page() -> None:
    """Render my new page."""
    st.title("My Page")
    # Add content
```

2. Add to sidebar navigation in `render_sidebar()`:
```python
pages = [
    "Overview",
    # ... existing pages ...
    "My Page",
]
```

3. Add to page routing in `main()`:
```python
elif selected_page == "My Page":
    render_my_page()
```

### Modifying the API client

1. Add method to `APIClient` class in `api_client.py`
2. Add corresponding cache function in `app.py`
3. Use cached function in render functions

## Code Quality

- Type hints throughout
- Docstrings for important functions
- Error handling on all API calls
- No hardcoded values (except configuration)
- Professional Python conventions

## Configuration

Application configuration:
- Page title: "APIx — India Real-Time Airfare Price Index"
- Page icon: ✈️
- Layout: Wide
- Sidebar: Expanded by default

API configuration:
- Base URL: `http://127.0.0.1:8000`
- Request timeout: 5 seconds
- Retry attempts: 2
- Cache TTL: 30 seconds

## Maintenance

### Regular tasks
- Monitor error logs
- Verify API connectivity
- Update dependencies periodically
- Test new data formats

### Updating dependencies
```bash
pip install --upgrade -r requirements.txt
```

## License

Part of the India Real-Time Airfare Price Index (APIx) project.
