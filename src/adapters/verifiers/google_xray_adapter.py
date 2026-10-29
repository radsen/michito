import urllib.parse

class GoogleXRayAdapter:
    def generate_linkedin_search_url(self, first_name: str, last_name: str, company: str) -> str:
        """
        Generates a Google X-Ray search URL for LinkedIn to verify if a person 
        works at a specific company.
        """
        query = f'site:linkedin.com/in/ "{first_name} {last_name}" "{company}"'
        encoded_query = urllib.parse.quote_plus(query)
        return f"https://www.google.com/search?q={encoded_query}"
