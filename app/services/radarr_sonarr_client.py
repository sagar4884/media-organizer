import requests
from urllib.parse import urljoin

class MediaClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {'X-Api-Key': self.api_key}

    def get_root_folders(self):
        """Fetch configured root folders from Radarr/Sonarr."""
        if not self.base_url or not self.api_key:
            return []
            
        endpoint = urljoin(self.base_url, 'api/v3/rootfolder')
        try:
            resp = requests.get(endpoint, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return [folder['path'] for folder in data]
        except Exception as e:
            print(f"Error fetching root folders: {e}")
            return []

    def get_library(self):
        """Fetch all movies or series."""
        pass # To be implemented by subclasses

class RadarrClient(MediaClient):
    def get_library(self):
        if not self.base_url or not self.api_key:
            return []
        
        endpoint = urljoin(self.base_url, 'api/v3/movie')
        try:
            resp = requests.get(endpoint, headers=self.headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error fetching Radarr library: {e}")
            return []

class SonarrClient(MediaClient):
    def get_library(self):
        if not self.base_url or not self.api_key:
            return []

        endpoint = urljoin(self.base_url, 'api/v3/series')
        try:
            resp = requests.get(endpoint, headers=self.headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error fetching Sonarr library: {e}")
            return []
