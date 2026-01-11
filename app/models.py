from app import db

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Radarr
    radarr_url = db.Column(db.String(255), nullable=True)
    radarr_api_key = db.Column(db.String(255), nullable=True)
    
    # Sonarr
    sonarr_url = db.Column(db.String(255), nullable=True)
    sonarr_api_key = db.Column(db.String(255), nullable=True)
    
    # Gemini
    gemini_api_key = db.Column(db.String(255), nullable=True)
    gemini_model = db.Column(db.String(100), default='gemini-1.5-flash')

class MediaItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.Integer, nullable=False) # Radarr/Sonarr ID
    tmdb_id = db.Column(db.Integer, nullable=True)
    
    # 'movie' or 'series'
    type = db.Column(db.String(20), nullable=False)
    
    title = db.Column(db.String(255), nullable=False)
    overview = db.Column(db.Text, nullable=True) # Useful for AI context
    
    current_path = db.Column(db.String(512), nullable=True)
    suggested_path = db.Column(db.String(512), nullable=True)
    
    is_organized = db.Column(db.Boolean, default=False)
    ignored = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'external_id': self.external_id,
            'title': self.title,
            'type': self.type,
            'current_path': self.current_path,
            'suggested_path': self.suggested_path,
            'is_organized': self.is_organized,
            'ignored': self.ignored
        }
