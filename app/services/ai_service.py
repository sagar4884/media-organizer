import google.generativeai as genai
import os

class AIService:
    def __init__(self, api_key, model_name='gemini-1.5-flash'):
        self.api_key = api_key
        self.model_name = model_name
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def analyze_media_location(self, title, tmdb_id, overview, root_folders):
        if not self.api_key:
            return None

        if not root_folders:
            return None

        folders_str = "\n".join(root_folders)
        
        prompt = f"""
        I have a media item that needs to be sorted into the correct root folder.
        
        Metadata:
        - Title: {title}
        - TMDB_ID: {tmdb_id}
        - Overview: {overview}
        
        Available Root Folders:
        {folders_str}
        
        Task:
        Based on the metadata (especially genre/theme implied by overview) and the folder names, 
        which root folder does this item belong in? 
        
        Constraints:
        - Return ONLY the exact folder path string from the list above.
        - Do not add explanations or quotes.
        - If unsure, pick the best logical match.
        """

        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            suggested_path = response.text.strip()
            
            # Simple validation: ensure the returned string is actually one of the options (or close to it)
            # Ideally, we check strict equality, but LLMs sometimes add whitespace.
            for folder in root_folders:
                if folder.strip() == suggested_path:
                    return folder
            
            # Fallback: if exact match fails, check if result is contained in folder path
            for folder in root_folders:
                if suggested_path in folder:
                    return folder

            return suggested_path 
        except Exception as e:
            print(f"Gemini AI Error: {e}")
            return None
