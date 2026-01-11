from google import genai
import os

class AIService:
    def __init__(self, api_key, model_name='gemini-2.0-flash-exp'):
        self.api_key = api_key
        # Use 'gemini-2.0-flash-exp' as default if not specified, or fallback to what user provides
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
        
        Specific Rules for 'Anime' vs 'Anime (R or MA)':
        1. If a folder named "Anime (R or MA)" exists:
           - Place content here IF it contains mature themes such as: excessive violence, gore, nudity, sexual content, strong drug use, or excessive strong language (e.g. Rick and Morty, Berserk, Goblin Slayer, Attack on Titan, South Park, Family Guy).
           - This applies to Western Animation (Cartoons) as well if they are mature (e.g., Archer, Rick and Morty).
        2. If a folder named "Anime" exists:
           - Place content here if it is animated (Japanese Anime, Donghua, or Western Cartoons) BUT is generally suitable for teenagers or general audiences (e.g., Naruto, One Piece, Avatar: The Last Airbender).
        3. If a folder named "English" exists:
           - Only put Live Action content here. Do NOT put animated content in "English" if an "Anime" folder exists.
        
        General Constraints:
        - Return ONLY the exact folder path string from the list above.
        - Do not add explanations or quotes.
        - If unsure, pick the best logical match based on the rules above.
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
