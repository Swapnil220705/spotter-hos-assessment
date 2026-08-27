const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export async function fetchPlanTrip(tripData) {
  const response = await fetch(`${API_BASE_URL}/plan-trip/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(tripData),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Server error: ${response.status}`);
  }

  return await response.json();
}

/**
 * Fetches location autocomplete suggestions from the backend proxy endpoint.
 * Pass an AbortSignal to cancel the request when the user continues typing.
 * Returns the suggestions array (may be empty). Throws on genuine network error.
 * AbortError is re-thrown so callers can distinguish cancellation from failure.
 */
export async function fetchLocationSuggestions(query, signal) {
  const url = `${API_BASE_URL}/location-suggestions/?q=${encodeURIComponent(query)}`;
  const response = await fetch(url, { signal });
  if (!response.ok) {
    // 400 means too-short query — return empty silently
    return [];
  }
  const data = await response.json();
  return data.suggestions || [];
}
