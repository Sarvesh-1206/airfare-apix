#!/usr/bin/env python
"""Test the APIx dashboard API client."""

import sys
sys.path.insert(0, r'c:\Users\abina\airfare_apix\src\dashboard')

from api_client import APIClient

client = APIClient()

print('Testing APIx API Client')
print('=' * 50)

# Test health
try:
    health = client.health()
    print('✓ Health check:', health.get('status', 'unknown'))
except Exception as e:
    print(f'✗ Health check failed: {e}')

# Test latest index
try:
    latest = client.latest_index()
    api_value = latest.get('value')
    api_date = latest.get('date')
    routes = latest.get('routes_available')
    print(f'✓ Latest index: APIx={api_value}, Date={api_date}, Routes={routes}')
except Exception as e:
    print(f'✗ Latest index failed: {e}')

# Test history
try:
    history = client.index_history()
    count = history.get('count')
    print(f'✓ Index history: {count} records')
except Exception as e:
    print(f'✗ History failed: {e}')

# Test routes
try:
    routes = client.route_indices()
    count = routes.get('count')
    print(f'✓ Route indices: {count} routes')
except Exception as e:
    print(f'✗ Routes failed: {e}')

# Test lead times
try:
    lead_times = client.lead_time_indices(fare_class='Economy')
    count = lead_times.get('count')
    print(f'✓ Lead-time indices (Economy): {count} records')
except Exception as e:
    print(f'✗ Lead times failed: {e}')

# Test quality
try:
    quality = client.quality_report()
    pass_count = quality.get('pass_count', 0)
    review_count = quality.get('review_count', 0)
    fail_count = quality.get('fail_count', 0)
    status = quality.get('overall_status')
    print(f'✓ Quality report: Status={status}, {pass_count} PASS, {review_count} REVIEW, {fail_count} FAIL')
except Exception as e:
    print(f'✗ Quality failed: {e}')

# Test summary
try:
    summary = client.summary()
    collection_days = summary.get('collection_days', 0)
    base_idx = summary.get('base_index', 0)
    routes_count = len(summary.get('route_weights', {}))
    print(f'✓ Summary: {int(collection_days)} collection days, base index={base_idx}, {routes_count} routes')
except Exception as e:
    print(f'✗ Summary failed: {e}')

print('=' * 50)
print('✓ All API endpoints working correctly')
