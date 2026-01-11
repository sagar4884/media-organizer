from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app import db
from app.models import Settings, MediaItem
from app.services.radarr_sonarr_client import RadarrClient, SonarrClient
from app.services.ai_service import AIService
from flask import current_app
from rq.job import Job

main = Blueprint('main', __name__)

# --- Helper Functions ---

def get_settings():
    s = Settings.query.first()
    if not s:
        s = Settings()
        db.session.add(s)
        db.session.commit()
    return s

# --- Background Tasks (RQ) ---

def sync_library_task(app_type):
    """
    Background task to fetch items from Radarr/Sonarr and update DB.
    app_type: 'radarr' or 'sonarr'
    """
    from app import create_app
    app = create_app()
    
    with app.app_context():
        settings = Settings.query.first()
        if not settings:
            return

        client = None
        if app_type == 'radarr':
            client = RadarrClient(settings.radarr_url, settings.radarr_api_key)
        else:
            client = SonarrClient(settings.sonarr_url, settings.sonarr_api_key)

        items = client.get_library()
        
        for item in items:
            external_id = item.get('id')
            title = item.get('title')
            path = item.get('path') # The full path including folder
            root_folder = item.get('rootFolderPath') # Should exist in newer *arr APIs, else parse path
            
            # Sonarr uses tvdbId usually, Radarr tmdbId
            tmdb_id = item.get('tmdbId') 
            if not tmdb_id and 'tvdbId' in item:
                tmdb_id = item.get('tvdbId') # Storing in same column for simplicity
                
            overview = item.get('overview')

            media_item = MediaItem.query.filter_by(external_id=external_id, type='movie' if app_type == 'radarr' else 'series').first()
            
            if not media_item:
                media_item = MediaItem(
                    external_id=external_id,
                    type='movie' if app_type == 'radarr' else 'series',
                    title=title,
                    current_path=root_folder if root_folder else path, # Try to store just the root part if possible
                    overview=overview,
                    tmdb_id=tmdb_id
                )
                db.session.add(media_item)
            else:
                # Update info
                media_item.current_path = root_folder if root_folder else path
                media_item.overview = overview
            
            # Simple check: if suggested path exists and matches current, it's organized
            if media_item.suggested_path and media_item.suggested_path == media_item.current_path:
                media_item.is_organized = True
            
        db.session.commit()

def analyze_item_task(item_id):
    from app import create_app
    app = create_app()
    
    with app.app_context():
        item = MediaItem.query.get(item_id)
        settings = Settings.query.first()
        
        if not item or not settings:
            return

        # Initialize Clients
        ai = AIService(settings.gemini_api_key, settings.gemini_model)
        
        client = None
        if item.type == 'movie':
            client = RadarrClient(settings.radarr_url, settings.radarr_api_key)
        else:
            client = SonarrClient(settings.sonarr_url, settings.sonarr_api_key)
            
        root_folders = client.get_root_folders()
        
        suggested = ai.analyze_media_location(item.title, item.tmdb_id, item.overview, root_folders)
        
        if suggested:
            item.suggested_path = suggested
            # Logic: If suggested matches current path (normalized), it is organized
            # Strip trailing slashes for comparison
            s_norm = suggested.rstrip('/')
            c_norm = (item.current_path or "").rstrip('/')
            
            if s_norm == c_norm:
                item.is_organized = True
            else:
                item.is_organized = False
                
            db.session.commit()


# --- Routes ---

@main.route('/')
def dashboard():
    settings = get_settings()
    total_items = MediaItem.query.count()
    organized_items = MediaItem.query.filter_by(is_organized=True).count()
    needs_attention = MediaItem.query.filter_by(is_organized=False, ignored=False).count()
    
    return render_template('dashboard.html', 
                           total=total_items, 
                           organized=organized_items, 
                           attention=needs_attention)

@main.route('/settings', methods=['GET', 'POST'])
def settings_page():
    settings = get_settings()
    
    if request.method == 'POST':
        settings.radarr_url = request.form.get('radarr_url')
        settings.radarr_api_key = request.form.get('radarr_api_key')
        settings.sonarr_url = request.form.get('sonarr_url')
        settings.sonarr_api_key = request.form.get('sonarr_api_key')
        settings.gemini_api_key = request.form.get('gemini_api_key')
        settings.gemini_model = request.form.get('gemini_model') or 'gemini-1.5-flash'
        
        db.session.commit()
        flash('Settings Saved!', 'success')
        return redirect(url_for('main.settings_page'))
        
    return render_template('settings.html', settings=settings)

@main.route('/test-connection', methods=['POST'])
def test_connection():
    # Simple test for settings page
    settings = get_settings()
    r_client = RadarrClient(settings.radarr_url, settings.radarr_api_key)
    s_client = SonarrClient(settings.sonarr_url, settings.sonarr_api_key)
    
    r_folders = r_client.get_root_folders()
    s_folders = s_client.get_root_folders()
    
    status = {
        'radarr': bool(r_folders),
        'sonarr': bool(s_folders)
    }
    return jsonify(status)

@main.route('/media/<media_type>')
def media_view(media_type):
    if media_type not in ['movie', 'series']:
        return redirect(url_for('main.dashboard'))
    
    # Sorting Logic
    sort_by = request.args.get('sort', 'title')
    order = request.args.get('order', 'asc')
    
    query = MediaItem.query.filter_by(type=media_type, is_organized=False, ignored=False)
    
    if sort_by == 'title':
        query = query.order_by(MediaItem.title.asc() if order == 'asc' else MediaItem.title.desc())
    elif sort_by == 'path':
        query = query.order_by(MediaItem.current_path.asc() if order == 'asc' else MediaItem.current_path.desc())
    elif sort_by == 'suggested':
        query = query.order_by(MediaItem.suggested_path.asc() if order == 'asc' else MediaItem.suggested_path.desc())
        
    items = query.all()
    
    return render_template('media_list.html', items=items, media_type=media_type, sort_by=sort_by, order=order)

@main.route('/sync/<media_type>', methods=['POST'])
def sync_media(media_type):
    target = 'radarr' if media_type == 'movie' else 'sonarr'
    # Enqueue job
    current_app.task_queue.enqueue(sync_library_task, target)
    flash(f'{target.capitalize()} Sync Started', 'info')
    return redirect(url_for('main.media_view', media_type=media_type))

@main.route('/analyze-all/<media_type>', methods=['POST'])
def analyze_all(media_type):
    items = MediaItem.query.filter_by(type=media_type, is_organized=False, ignored=False).all()
    count = 0
    for item in items:
        current_app.task_queue.enqueue(analyze_item_task, item.id)
        count += 1
    
    flash(f'Queued analysis for {count} items.', 'info')
    return redirect(url_for('main.media_view', media_type=media_type))

@main.route('/analyze-quick/<media_type>', methods=['POST'])
def analyze_quick(media_type):
    # Only analyze items that don't have a suggested path yet
    items = MediaItem.query.filter_by(type=media_type, is_organized=False, ignored=False).filter(MediaItem.suggested_path == None).all()
    count = 0
    for item in items:
        current_app.task_queue.enqueue(analyze_item_task, item.id)
        count += 1
    
    flash(f'Queued quick analysis for {count} new items.', 'info')
    return redirect(url_for('main.media_view', media_type=media_type))

@main.route('/analyze-selected', methods=['POST'])
def analyze_selected():
    item_ids = request.form.getlist('item_ids')
    
    if not item_ids:
        flash('No items selected.', 'warning')
        return redirect(request.referrer or url_for('main.dashboard'))
    
    count = 0
    for item_id in item_ids:
        current_app.task_queue.enqueue(analyze_item_task, int(item_id))
        count += 1
    
    flash(f'Queued analysis for {count} selected items.', 'info')
    return redirect(request.referrer)

@main.route('/action/ignore/<int:item_id>', methods=['POST'])
def ignore_item(item_id):
    item = MediaItem.query.get_or_404(item_id)
    item.ignored = True
    db.session.commit()
    return '', 200 # HTMX expects empty or partial response to remove element usually, or we can refresh

@main.route('/action/rescan/<int:item_id>', methods=['POST'])
def rescan_item(item_id):
    current_app.task_queue.enqueue(analyze_item_task, item_id)
    return '<span class="text-blue-400">Queued...</span>', 200

@main.route('/status/queue')
def queue_status():
    """Returns the number of jobs in the queue."""
    count = len(current_app.task_queue)
    return jsonify({'count': count})

@main.route('/status/stop', methods=['POST'])
def stop_queue():
    """Empties the queue."""
    current_app.task_queue.empty()
    flash('Queue cleared!', 'warning')
    return redirect(request.referrer or url_for('main.dashboard'))
