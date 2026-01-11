from google import genai
import os

class AIService:
    def __init__(self, api_key, model_name='gemini-2.0-flash-exp'):
        self.api_key = api_key
        # Use 'gemini-2.0-flash-exp' as default if not specified, or fallback to what user provides
        # The new SDK might use different model identifiers, but 'gemini-2.0-flash-exp' is a safe bet for newer usage.
        # If the user has 'gemini-1.5-flash' in settings, it might still fail if not supported by the new SDK/endpoint context.
        # Let's try to stick to what the user provides, but default to a known working one if empty.
        self.model_name = model_name if model_name else 'gemini-2.0-flash-exp'
        
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

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
            # New SDK usage
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            suggested_path = response.text.strip()
            
            # Simple validation: ensure the returned string is actually one of the options (or close to it)
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
