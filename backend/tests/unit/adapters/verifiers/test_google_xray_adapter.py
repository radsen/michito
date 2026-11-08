from src.adapters.verifiers.google_xray_adapter import GoogleXRayAdapter
import urllib.parse

def test_generate_linkedin_search_url():
    adapter = GoogleXRayAdapter()
    url = adapter.generate_linkedin_search_url("John", "Doe", "Acme Corp")
    
    expected_query = 'site:linkedin.com/in/ "John Doe" "Acme Corp"'
    encoded_query = urllib.parse.quote_plus(expected_query)
    
    assert url == f"https://www.google.com/search?q={encoded_query}"
