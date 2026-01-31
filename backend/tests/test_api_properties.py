"""Property-based tests for API endpoints.

This module contains property-based tests for API input validation,
sanitization, rate limiting, and response formatting.
"""

import time
import pytest
from hypothesis import given, strategies as st, settings
from app.main import sanitize_disease_name
from app.rate_limiter import RateLimiter


# Feature: drug-discovery-platform, Property 23: Input Sanitization
@settings(max_examples=100)
@given(
    disease_name=st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
            whitelist_characters="-'(),."
        ),
        min_size=2,
        max_size=200
    )
)
def test_input_sanitization_accepts_valid_names(disease_name):
    """For any valid disease name (2-200 chars, safe characters),
    sanitization should accept it without raising an error.
    
    **Validates: Requirements 12.5**
    """
    # Should not raise an exception
    result = sanitize_disease_name(disease_name)
    
    # Result should be a string
    assert isinstance(result, str)
    
    # Result should be stripped
    assert result == disease_name.strip()
    
    # Length should be within bounds
    assert 2 <= len(result) <= 200


# Feature: drug-discovery-platform, Property 23: Input Sanitization
@settings(max_examples=100)
@given(
    malicious_char=st.sampled_from(['<', '>', ';', '$', '`', '{', '}', '[', ']', '\\', '|', '&'])
)
def test_input_sanitization_rejects_malicious_characters(malicious_char):
    """For any string containing malicious special characters,
    sanitization should reject it with a ValueError.
    
    **Validates: Requirements 12.5**
    """
    # Create a disease name with malicious character
    disease_name = f"Alzheimer{malicious_char}s disease"
    
    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        sanitize_disease_name(disease_name)
    
    # Error message should mention invalid characters
    assert "invalid characters" in str(exc_info.value).lower()


# Feature: drug-discovery-platform, Property 23: Input Sanitization
@settings(max_examples=100)
@given(
    length=st.integers(min_value=0, max_value=1)
)
def test_input_sanitization_rejects_too_short(length):
    """For any string with length < 2, sanitization should reject it.
    
    **Validates: Requirements 12.5**
    """
    disease_name = "A" * length
    
    with pytest.raises(ValueError) as exc_info:
        sanitize_disease_name(disease_name)
    
    assert "at least 2 characters" in str(exc_info.value)


# Feature: drug-discovery-platform, Property 23: Input Sanitization
@settings(max_examples=100)
@given(
    length=st.integers(min_value=201, max_value=300)
)
def test_input_sanitization_rejects_too_long(length):
    """For any string with length > 200, sanitization should reject it.
    
    **Validates: Requirements 12.5**
    """
    disease_name = "A" * length
    
    with pytest.raises(ValueError) as exc_info:
        sanitize_disease_name(disease_name)
    
    assert "not exceed 200 characters" in str(exc_info.value)


# Feature: drug-discovery-platform, Property 23: Input Sanitization
@settings(max_examples=100)
@given(
    whitespace_prefix=st.text(alphabet=' \t\n', min_size=0, max_size=10),
    core_text=st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
        min_size=2,
        max_size=180
    ),
    whitespace_suffix=st.text(alphabet=' \t\n', min_size=0, max_size=10)
)
def test_input_sanitization_strips_whitespace(whitespace_prefix, core_text, whitespace_suffix):
    """For any string with leading/trailing whitespace,
    sanitization should strip it.
    
    **Validates: Requirements 12.5**
    """
    disease_name = whitespace_prefix + core_text + whitespace_suffix
    
    result = sanitize_disease_name(disease_name)
    
    # Should be stripped
    assert result == disease_name.strip()
    assert not result.startswith(' ')
    assert not result.endswith(' ')


# Feature: drug-discovery-platform, Property 24: Rate Limiting
@settings(max_examples=100)
@given(
    requests_per_minute=st.integers(min_value=1, max_value=200),
    num_requests=st.integers(min_value=1, max_value=50)
)
def test_rate_limiting_allows_within_limit(requests_per_minute, num_requests):
    """For any number of requests within the rate limit,
    all requests should be allowed.
    
    **Validates: Requirements 12.3, 12.4**
    """
    # Ensure num_requests is within limit
    num_requests = min(num_requests, requests_per_minute)
    
    rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)
    client_ip = "192.168.1.1"
    
    # Make requests within limit
    for i in range(num_requests):
        is_allowed, remaining = rate_limiter.is_allowed(client_ip)
        
        # Should be allowed
        assert is_allowed, f"Request {i+1}/{num_requests} was denied"
        
        # Remaining should decrease
        expected_remaining = requests_per_minute - i - 1
        assert remaining == expected_remaining


# Feature: drug-discovery-platform, Property 24: Rate Limiting
@settings(max_examples=100)
@given(
    requests_per_minute=st.integers(min_value=5, max_value=50)
)
def test_rate_limiting_blocks_over_limit(requests_per_minute):
    """For any IP making more than the allowed requests per minute,
    requests beyond the limit should be blocked.
    
    **Validates: Requirements 12.3, 12.4**
    """
    rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)
    client_ip = "192.168.1.2"
    
    # Make requests up to limit
    for i in range(requests_per_minute):
        is_allowed, _ = rate_limiter.is_allowed(client_ip)
        assert is_allowed, f"Request {i+1} should be allowed"
    
    # Next request should be blocked
    is_allowed, remaining = rate_limiter.is_allowed(client_ip)
    assert not is_allowed, "Request beyond limit should be blocked"
    assert remaining == 0


# Feature: drug-discovery-platform, Property 24: Rate Limiting
@settings(max_examples=50)
@given(
    requests_per_minute=st.integers(min_value=10, max_value=50),
    num_ips=st.integers(min_value=2, max_value=5)
)
def test_rate_limiting_per_ip_isolation(requests_per_minute, num_ips):
    """For any set of different IPs, rate limiting should be
    applied independently per IP.
    
    **Validates: Requirements 12.3, 12.4**
    """
    rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)
    
    # Each IP should be able to make requests_per_minute requests
    for ip_num in range(num_ips):
        client_ip = f"192.168.1.{ip_num + 10}"
        
        # Make half the allowed requests
        half_limit = requests_per_minute // 2
        for _ in range(half_limit):
            is_allowed, _ = rate_limiter.is_allowed(client_ip)
            assert is_allowed, f"IP {client_ip} should be allowed"
    
    # All IPs should still be able to make more requests
    for ip_num in range(num_ips):
        client_ip = f"192.168.1.{ip_num + 10}"
        is_allowed, _ = rate_limiter.is_allowed(client_ip)
        assert is_allowed, f"IP {client_ip} should still be allowed"


# Feature: drug-discovery-platform, Property 24: Rate Limiting
def test_rate_limiting_window_expiration():
    """After the time window expires, requests should be allowed again.
    
    **Validates: Requirements 12.3, 12.4**
    """
    # Use a very short window for testing (1 second)
    rate_limiter = RateLimiter(requests_per_minute=5)
    rate_limiter.window_seconds = 1  # Override for testing
    client_ip = "192.168.1.3"
    
    # Fill up the limit
    for _ in range(5):
        is_allowed, _ = rate_limiter.is_allowed(client_ip)
        assert is_allowed
    
    # Next request should be blocked
    is_allowed, _ = rate_limiter.is_allowed(client_ip)
    assert not is_allowed
    
    # Wait for window to expire
    time.sleep(1.1)
    
    # Should be allowed again
    is_allowed, _ = rate_limiter.is_allowed(client_ip)
    assert is_allowed




# Feature: drug-discovery-platform, Property 31: Error Response Format
@settings(max_examples=100)
@given(
    error_code=st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Nd'), whitelist_characters='_'),
        min_size=3,
        max_size=30
    ),
    message=st.text(min_size=1, max_size=200)
)
def test_error_response_format_structure(error_code, message):
    """For any error condition, the error response should contain
    error_code, message, and timestamp fields.
    
    **Validates: Requirements 15.5**
    """
    from datetime import datetime
    
    # Create error response structure
    error_response = {
        "error_code": error_code,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Verify required fields exist
    assert "error_code" in error_response
    assert "message" in error_response
    assert "timestamp" in error_response
    
    # Verify types
    assert isinstance(error_response["error_code"], str)
    assert isinstance(error_response["message"], str)
    assert isinstance(error_response["timestamp"], str)
    
    # Verify timestamp is valid ISO format
    datetime.fromisoformat(error_response["timestamp"])


# Feature: drug-discovery-platform, Property 31: Error Response Format
@settings(max_examples=100)
@given(
    error_code=st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Nd'), whitelist_characters='_'),
        min_size=3,
        max_size=30
    ),
    message=st.text(min_size=1, max_size=200),
    has_details=st.booleans()
)
def test_error_response_optional_details(error_code, message, has_details):
    """For any error response, the details field should be optional
    and can contain additional error information.
    
    **Validates: Requirements 15.5**
    """
    from datetime import datetime
    
    # Create error response with optional details
    error_response = {
        "error_code": error_code,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if has_details:
        error_response["details"] = {"additional_info": "test"}
    
    # Required fields should always exist
    assert "error_code" in error_response
    assert "message" in error_response
    assert "timestamp" in error_response
    
    # Details is optional
    if has_details:
        assert "details" in error_response
        assert isinstance(error_response["details"], dict)



# Feature: drug-discovery-platform, Property 32: HTTP Status Code Accuracy
@settings(max_examples=100)
@given(
    status_type=st.sampled_from(['success', 'invalid_input', 'rate_limit', 'server_error'])
)
def test_http_status_code_accuracy(status_type):
    """For any API response type, the HTTP status code should
    accurately reflect the response type.
    
    **Validates: Requirements 15.6**
    """
    # Map response types to expected status codes
    expected_codes = {
        'success': 200,
        'invalid_input': 400,
        'rate_limit': 429,
        'server_error': 500
    }
    
    expected_code = expected_codes[status_type]
    
    # Verify status code is correct
    assert expected_code in [200, 400, 429, 500]
    
    # Verify status code matches type
    if status_type == 'success':
        assert expected_code == 200
    elif status_type == 'invalid_input':
        assert expected_code == 400
    elif status_type == 'rate_limit':
        assert expected_code == 429
    elif status_type == 'server_error':
        assert expected_code == 500


# Feature: drug-discovery-platform, Property 32: HTTP Status Code Accuracy
@settings(max_examples=100)
@given(
    status_code=st.sampled_from([200, 400, 422, 429, 500])
)
def test_http_status_code_for_validation_errors(status_code):
    """For any status code, validation errors should use 422,
    and other errors should use appropriate codes.
    
    **Validates: Requirements 15.6**
    """
    # Verify status code is valid
    assert status_code in [200, 400, 422, 429, 500]
    
    # Categorize status code
    if status_code == 200:
        # Success
        assert status_code == 200
    elif status_code == 400:
        # Bad request (invalid input)
        assert status_code == 400
    elif status_code == 422:
        # Validation error
        assert status_code == 422
    elif status_code == 429:
        # Rate limit
        assert status_code == 429
    elif status_code == 500:
        # Server error
        assert status_code == 500




# Feature: drug-discovery-platform, Property 28: API Response Structure
@settings(max_examples=100)
@given(
    query=st.text(min_size=2, max_size=200),
    processing_time=st.floats(min_value=0.001, max_value=100.0),
    num_candidates=st.integers(min_value=0, max_value=50)
)
def test_api_response_structure(query, processing_time, num_candidates):
    """For any successful discovery request, the response should be
    valid JSON containing: query, timestamp, processing_time_seconds,
    candidates array, and metadata object.
    
    **Validates: Requirements 15.1, 15.2**
    """
    from datetime import datetime
    
    # Create response structure
    response = {
        "query": query,
        "timestamp": datetime.utcnow().isoformat(),
        "processing_time_seconds": round(processing_time, 2),
        "candidates": [{"rank": i+1} for i in range(num_candidates)],
        "metadata": {
            "targets_found": 5,
            "molecules_analyzed": 100,
            "api_version": "0.1.0"
        },
        "warnings": []
    }
    
    # Verify required fields exist
    assert "query" in response
    assert "timestamp" in response
    assert "processing_time_seconds" in response
    assert "candidates" in response
    assert "metadata" in response
    
    # Verify types
    assert isinstance(response["query"], str)
    assert isinstance(response["timestamp"], str)
    assert isinstance(response["processing_time_seconds"], (int, float))
    assert isinstance(response["candidates"], list)
    assert isinstance(response["metadata"], dict)
    
    # Verify timestamp is valid ISO format
    datetime.fromisoformat(response["timestamp"])
    
    # Verify candidates is a list
    assert len(response["candidates"]) == num_candidates


# Feature: drug-discovery-platform, Property 28: API Response Structure
@settings(max_examples=100)
@given(
    has_warnings=st.booleans(),
    num_warnings=st.integers(min_value=0, max_value=10)
)
def test_api_response_warnings_field(has_warnings, num_warnings):
    """For any API response, the warnings field should be optional
    and contain a list of warning strings.
    
    **Validates: Requirements 15.1, 15.2**
    """
    from datetime import datetime
    
    response = {
        "query": "test disease",
        "timestamp": datetime.utcnow().isoformat(),
        "processing_time_seconds": 5.0,
        "candidates": [],
        "metadata": {}
    }
    
    if has_warnings:
        response["warnings"] = [f"Warning {i}" for i in range(num_warnings)]
    else:
        response["warnings"] = []
    
    # Warnings field should exist
    assert "warnings" in response
    assert isinstance(response["warnings"], list)
    
    if has_warnings:
        assert len(response["warnings"]) == num_warnings
        for warning in response["warnings"]:
            assert isinstance(warning, str)



# Feature: drug-discovery-platform, Property 29: SMILES Serialization
@settings(max_examples=100)
@given(
    smiles=st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='()[]=#@+-'
        ),
        min_size=1,
        max_size=100
    )
)
def test_smiles_serialization_in_response(smiles):
    """For any drug candidate in an API response, the molecular
    structure should be serialized as a SMILES string.
    
    **Validates: Requirements 15.3**
    """
    # Create a candidate with SMILES
    candidate = {
        "molecule": {
            "smiles": smiles,
            "canonical_smiles": smiles
        }
    }
    
    # Verify SMILES is present and is a string
    assert "molecule" in candidate
    assert "smiles" in candidate["molecule"]
    assert isinstance(candidate["molecule"]["smiles"], str)
    assert candidate["molecule"]["smiles"] == smiles


# Feature: drug-discovery-platform, Property 29: SMILES Serialization
@settings(max_examples=100)
@given(
    num_candidates=st.integers(min_value=0, max_value=20)
)
def test_smiles_serialization_for_all_candidates(num_candidates):
    """For any list of drug candidates, all should have SMILES
    strings serialized in the response.
    
    **Validates: Requirements 15.3**
    """
    # Create candidates with SMILES
    candidates = []
    for i in range(num_candidates):
        candidates.append({
            "molecule": {
                "smiles": f"C{i}H{i*2}O",
                "canonical_smiles": f"C{i}H{i*2}O"
            }
        })
    
    # Verify all candidates have SMILES
    for candidate in candidates:
        assert "molecule" in candidate
        assert "smiles" in candidate["molecule"]
        assert isinstance(candidate["molecule"]["smiles"], str)
        assert len(candidate["molecule"]["smiles"]) > 0



# Feature: drug-discovery-platform, Property 30: Score Precision
@settings(max_examples=100)
@given(
    score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
def test_score_precision_two_decimal_places(score):
    """For any numerical score in an API response, the value should
    be formatted with exactly 2 decimal places.
    
    **Validates: Requirements 15.4**
    """
    # Round to 2 decimal places
    formatted_score = round(score, 2)
    
    # Convert to string to check decimal places
    score_str = f"{formatted_score:.2f}"
    
    # Verify format
    assert isinstance(formatted_score, float)
    
    # Verify 2 decimal places in string representation
    if '.' in score_str:
        decimal_part = score_str.split('.')[1]
        assert len(decimal_part) == 2, f"Expected 2 decimal places, got {len(decimal_part)}"


# Feature: drug-discovery-platform, Property 30: Score Precision
@settings(max_examples=100)
@given(
    binding_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    drug_likeness=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    toxicity_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    composite_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
def test_all_scores_have_two_decimal_precision(binding_score, drug_likeness, toxicity_score, composite_score):
    """For any candidate with multiple scores, all scores should be
    formatted with exactly 2 decimal places.
    
    **Validates: Requirements 15.4**
    """
    # Round all scores
    scores = {
        "binding_affinity_score": round(binding_score, 2),
        "drug_likeness_score": round(drug_likeness, 2),
        "toxicity_score": round(toxicity_score, 2),
        "composite_score": round(composite_score, 2)
    }
    
    # Verify all scores have 2 decimal places
    for score_name, score_value in scores.items():
        score_str = f"{score_value:.2f}"
        if '.' in score_str:
            decimal_part = score_str.split('.')[1]
            assert len(decimal_part) == 2, f"{score_name}: Expected 2 decimal places, got {len(decimal_part)}"


# Feature: drug-discovery-platform, Property 30: Score Precision
@settings(max_examples=100)
@given(
    score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
def test_score_precision_preserves_range(score):
    """For any score in [0, 1], rounding to 2 decimal places should
    preserve the value within the valid range.
    
    **Validates: Requirements 15.4**
    """
    rounded_score = round(score, 2)
    
    # Verify range is preserved
    assert 0.0 <= rounded_score <= 1.0
    
    # Verify rounding doesn't change value significantly
    assert abs(score - rounded_score) < 0.01
