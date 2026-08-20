import os
import uuid
import math
from io import BytesIO
from datetime import datetime, timezone
from flask import (Flask, render_template, redirect, url_for, flash, request,
                   jsonify, abort, current_app)
from flask_login import (LoginManager, login_user, logout_user, login_required,
                         current_user)
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from PIL import Image
from sqlalchemy import func
import requests

import cloudinary
from cloudinary.uploader import upload
from cloudinary.api import delete_resources

from config import Config
from models import (db, User, Place, VibeCheck, VibeTag, VibeCheckTag,
                    SavedPlace, Report, VibePhoto)


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    # Configure Cloudinary
    cloudinary.config(
        cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
        api_key=app.config['CLOUDINARY_API_KEY'],
        api_secret=app.config['CLOUDINARY_API_SECRET'],
        secure=True
    )

    db.init_app(app)
    csrf = CSRFProtect(app)

    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.login_message = 'Login to drop a vibe 🔥'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ---- Helpers ----

    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    def process_image(fileobj, max_size=(1200, 1200), quality=85):
        img = Image.open(fileobj)
        img.thumbnail(max_size, Image.LANCZOS)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=quality)
        buf.seek(0)
        return buf

    def upload_to_cloudinary(fileobj, folder='vibes'):
        try:
            processed = process_image(fileobj)
            result = upload(
                processed,
                folder=f"{app.config['CLOUDINARY_FOLDER']}/{folder}",
                format='jpg',
                quality='auto:good',
                width=1200,
                height=1200,
                crop='limit',
                eager=[{'width': 400, 'height': 400, 'crop': 'limit'}]
            )
            return {
                'url': result.get('secure_url'),
                'thumbnail': result.get('eager', [{}])[0].get('secure_url') if result.get('eager') else result.get('secure_url'),
                'public_id': result.get('public_id')
            }
        except Exception as e:
            print(f"Cloudinary upload error: {e}")
            return None

    def delete_from_cloudinary(public_id):
        try:
            if public_id:
                delete_resources([public_id])
        except Exception as e:
            print(f"Cloudinary delete error: {e}")

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def format_distance(meters):
        if meters < 1000:
            return f"{int(meters)} m"
        return f"{meters/1000:.1f} km"

    CATEGORY_MAP = {
        'chai': {'emoji': '☕', 'label': 'Chai', 'query': 'chai tea stall'},
        'cafe': {'emoji': '☕', 'label': 'Café', 'type': 'cafe'},
        'restaurant': {'emoji': '🍽️', 'label': 'Restaurant', 'type': 'restaurant'},
        'hangout': {'emoji': '🎉', 'label': 'Hangout', 'query': 'hangout places'},
    }

    JAIPUR_AREAS = [
        {'name': 'MI Road', 'lat': 26.9239, 'lng': 75.8266, 'emoji': '🛍️'},
        {'name': 'C-Scheme', 'lat': 26.9124, 'lng': 75.7873, 'emoji': '🏛️'},
        {'name': 'Raja Park', 'lat': 26.8775, 'lng': 75.8048, 'emoji': '🍽️'},
        {'name': 'Vaishali Nagar', 'lat': 26.8677, 'lng': 75.7606, 'emoji': '🏘️'},
        {'name': 'Malviya Nagar', 'lat': 26.8550, 'lng': 75.7950, 'emoji': '☕'},
        {'name': 'Mansarovar', 'lat': 26.8467, 'lng': 75.7700, 'emoji': '🏠'},
        {'name': 'Tonk Road', 'lat': 26.8530, 'lng': 75.8100, 'emoji': '🛣️'},
        {'name': 'Jagatpura', 'lat': 26.8350, 'lng': 75.8150, 'emoji': '📖'},
        {'name': 'Civil Lines', 'lat': 26.9190, 'lng': 75.8000, 'emoji': '🌳'},
        {'name': 'Sodala', 'lat': 26.8930, 'lng': 75.7560, 'emoji': '🚶'},
        {'name': 'Jhotwara', 'lat': 26.9400, 'lng': 75.7400, 'emoji': '🏘️'},
        {'name': 'Sanganer', 'lat': 26.8200, 'lng': 75.7800, 'emoji': '✈️'},
        {'name': 'Pratap Nagar', 'lat': 26.8300, 'lng': 75.7450, 'emoji': '🏘️'},
        {'name': 'Vidhyadhar Nagar', 'lat': 26.9450, 'lng': 75.7700, 'emoji': '🏘️'},
        {'name': 'Bani Park', 'lat': 26.9280, 'lng': 75.8050, 'emoji': '🏨'},
        {'name': 'Adarsh Nagar', 'lat': 26.9350, 'lng': 75.7900, 'emoji': '🏘️'},
        {'name': 'Nahargarh Road', 'lat': 26.9350, 'lng': 75.8400, 'emoji': '🏔️'},
        {'name': 'Pink City', 'lat': 26.9220, 'lng': 75.8260, 'emoji': '🏛️'},
        {'name': 'Jawahar Nagar', 'lat': 26.9100, 'lng': 75.7650, 'emoji': '🏘️'},
        {'name': 'Shyam Nagar', 'lat': 26.8700, 'lng': 75.7800, 'emoji': '🚶'},
    ]

    def google_search(query, lat=None, lng=None, category=None, page_token=None):
        key = app.config['GOOGLE_PLACES_API_KEY']
        if not key:
            return [], None
        url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
        params = {'key': key, 'query': query}
        if page_token:
            params['pagetoken'] = page_token
        else:
            if lat is not None and lng is not None:
                params['location'] = f'{lat},{lng}'
                params['radius'] = '5000'
            if category and category in CATEGORY_MAP:
                cat = CATEGORY_MAP[category]
                if 'type' in cat:
                    params['type'] = cat['type']
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get('status') != 'OK' and not data.get('next_page_token'):
                return [], None
            results = data.get('results', [])
            next_token = data.get('next_page_token')
            return results, next_token
        except Exception:
            return [], None

    def google_place_details(place_id):
        key = app.config['GOOGLE_PLACES_API_KEY']
        if not key:
            return None
        url = 'https://maps.googleapis.com/maps/api/place/details/json'
        params = {
            'key': key,
            'place_id': place_id,
            'fields': 'name,formatted_address,geometry,rating,price_level,photos,types'
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get('status') != 'OK':
                return None
            return data.get('result')
        except Exception:
            return None

    def google_photo_url(photo_ref, max_width=400):
        key = app.config['GOOGLE_PLACES_API_KEY']
        if not key or not photo_ref:
            return None
        return (f'https://maps.googleapis.com/maps/api/place/photo'
                f'?maxwidth={max_width}&photoreference={photo_ref}&key={key}')

    def detect_category(types, name=''):
        name_lower = name.lower()
        if any(t in name_lower for t in ['chai', 'tea', 'tapri', 'chaha']):
            return 'chai'
        if 'cafe' in types or 'coffee_shop' in types:
            return 'cafe'
        if 'restaurant' in types:
            return 'restaurant'
        if any(t in types for t in ['park', 'shopping_mall', 'movie_theater',
                                     'amusement_park', 'bowling_alley', 'spa',
                                     'night_club', 'bar']):
            return 'hangout'
        if 'cafe' in name_lower or 'coffee' in name_lower:
            return 'cafe'
        if 'restaurant' in name_lower or 'dhaba' in name_lower:
            return 'restaurant'
        return 'hangout'

    def get_or_create_place(google_data, category_override=None):
        gpid = google_data.get('place_id')
        place = Place.query.filter_by(google_place_id=gpid).first()
        if place:
            if google_data.get('rating'):
                place.google_rating = google_data['rating']
            if google_data.get('formatted_address'):
                place.address = google_data['formatted_address']
            db.session.commit()
            return place

        geo = google_data.get('geometry', {}).get('location', {})
        photo_ref = ''
        photos = google_data.get('photos', [])
        if photos:
            photo_ref = photos[0].get('photo_reference', '')

        cat = category_override or detect_category(
            google_data.get('types', []),
            google_data.get('name', '')
        )

        place = Place(
            google_place_id=gpid,
            name=google_data.get('name', 'Unknown Place'),
            category=cat,
            address=google_data.get('formatted_address', ''),
            latitude=geo.get('lat'),
            longitude=geo.get('lng'),
            google_rating=google_data.get('rating'),
            price_level=google_data.get('price_level'),
            photo_reference=photo_ref,
        )
        db.session.add(place)
        db.session.commit()
        return place

    def seed_tags():
        tags_data = [
            ('Chill', '☕'), ('Lit', '🔥'), ('Date-worthy', '❤️'),
            ('Friends', '👯'), ('Budget', '💸'), ('Aesthetic', '✨'),
            ('Good Music', '🎶'), ('Late Night', '🌙'), ('Great Food', '😋'),
            ('Instagrammable', '📸'), ('Quiet', '😴'),
            ('Good for Conversations', '🗣️'), ('Crowded', '🚫'),
        ]
        for name, emoji in tags_data:
            if not VibeTag.query.filter_by(name=name).first():
                db.session.add(VibeTag(name=name, emoji=emoji))
        db.session.commit()

    def send_telegram_notification(vc, place):
        bot_token = app.config.get('TELEGRAM_BOT_TOKEN', '')
        channel_id = app.config.get('TELEGRAM_CHANNEL_ID', '')
        if not bot_token or not channel_id:
            return
        try:
            photo = vc.photos.first()
            cat_label = {'chai': '☕ Chai', 'cafe': '☕ Café',
                         'restaurant': '🍽️ Restaurant', 'hangout': '🎉 Hangout'}
            text = (
                f"🔥 <b>NEW VIBE CHECK</b>\n\n"
                f"📍 {place.name}\n"
                f"{cat_label.get(place.category, '')}\n"
                f"⭐ {vc.rating}/5\n"
                f"👤 {vc.user.username}\n"
            )
            if vc.location_verified:
                text += "📍 Location Verified\n"
            if vc.review_text:
                text += f"\n💬 \"{vc.review_text}\""
            
            photo_url = photo.filename if photo else None
            
            if photo_url:
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                    data={'chat_id': channel_id, 'photo': photo_url,
                          'caption': text, 'parse_mode': 'HTML'},
                    timeout=10
                )
            else:
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data={'chat_id': channel_id, 'text': text, 'parse_mode': 'HTML'},
                    timeout=10
                )
        except Exception:
            pass

    # ---- Context Processor ----

    @app.context_processor
    def inject_globals():
        return {
            'categories': CATEGORY_MAP,
            'format_distance': format_distance,
            'jaipur_areas': JAIPUR_AREAS,
        }

    # ---- Routes ----

    @app.route('/')
    def index():
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)

        trending = []
        if lat and lng:
            places = Place.query.filter(
                Place.vibe_checks.any()
            ).all()
            scored = []
            for p in places:
                dist = haversine(lat, lng, p.latitude, p.longitude) if p.latitude and p.longitude else 99999
                if dist > 15000:
                    continue
                vc_count = p.vibe_check_count
                recent = p.vibe_checks.order_by(VibeCheck.created_at.desc()).first()
                recency = 0
                if recent:
                    hours = (datetime.now(timezone.utc) - recent.created_at).total_seconds() / 3600
                    recency = max(0, 100 - hours)
                score = (p.vibe_score or 0) * 0.4 + min(vc_count, 50) * 2 * 0.3 + recency * 0.3
                scored.append((p, dist, score))
            scored.sort(key=lambda x: x[2], reverse=True)
            trending = scored[:12]
        else:
            vc_count_sub = db.session.query(
                VibeCheck.place_id,
                func.count(VibeCheck.id).label('cnt')
            ).group_by(VibeCheck.place_id).subquery()

            places = db.session.query(Place).join(
                vc_count_sub, Place.id == vc_count_sub.c.place_id
            ).order_by(vc_count_sub.c.cnt.desc()).limit(12).all()
            trending = [(p, 0, 0) for p in places]

        return render_template('index.html', trending=trending, lat=lat, lng=lng)

    @app.route('/area/<area_name>')
    def area_search(area_name):
        area = None
        for a in JAIPUR_AREAS:
            if a['name'].lower().replace(' ', '-') == area_name.lower().replace(' ', '-'):
                area = a
                break
        if not area:
            abort(404)

        lat = area['lat']
        lng = area['lng']
        filter_cat = request.args.get('category', '').strip()

        cats_to_search = []
        if filter_cat and filter_cat in CATEGORY_MAP:
            cats_to_search = [filter_cat]
        else:
            cats_to_search = list(CATEGORY_MAP.keys())

        all_results = []
        for cat_key in cats_to_search:
            ci = CATEGORY_MAP[cat_key]
            query_str = f"{ci.get('query', ci.get('label', ''))} in {area['name']} Jaipur"
            gresults, _ = google_search(query_str, lat, lng, cat_key)
            for gr in gresults:
                place = get_or_create_place(gr, cat_key)
                dist = haversine(lat, lng, place.latitude, place.longitude) if place.latitude and place.longitude else 0
                all_results.append((place, dist))

        all_results.sort(
            key=lambda x: ((x[0].vibe_score or 0) * 10 + (x[0].google_rating or 0) * 5 - x[1] * 0.001),
            reverse=True
        )

        return render_template('search.html', results=all_results, q='',
                               cat='', lat=lat, lng=lng, page=1,
                               next_page_token=None, has_results=len(all_results) > 0,
                               base_params={},
                               area_name=area['name'], area_emoji=area['emoji'],
                               filter_cat=filter_cat)

    @app.route('/search')
    def search():
        q = request.args.get('q', '').strip()
        cat = request.args.get('category', '').strip()
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        page_token = request.args.get('page_token', '').strip()
        page = request.args.get('page', 1, type=int)

        results = []
        next_page_token = None
        has_results = False

        if q or cat:
            if cat in CATEGORY_MAP:
                ci = CATEGORY_MAP[cat]
                query_str = ci.get('query', ci.get('label', ''))
                if q:
                    query_str = f"{q} {query_str}"
                gresults, next_page_token = google_search(query_str, lat, lng, cat, page_token)
            elif q:
                gresults, next_page_token = google_search(q, lat, lng, page_token=page_token)
            else:
                gresults, next_page_token = [], None

            for gr in gresults:
                place = get_or_create_place(gr, cat if cat in CATEGORY_MAP else None)
                dist = 0
                if lat and lng and place.latitude and place.longitude:
                    dist = haversine(lat, lng, place.latitude, place.longitude)
                results.append((place, dist))

            has_results = len(results) > 0

        base_params = {}
        if q:
            base_params['q'] = q
        if cat:
            base_params['category'] = cat
        if lat:
            base_params['lat'] = lat
        if lng:
            base_params['lng'] = lng

        return render_template('search.html', results=results, q=q, cat=cat,
                               lat=lat, lng=lng, page=page,
                               next_page_token=next_page_token,
                               has_results=has_results,
                               base_params=base_params)

    @app.route('/place/<google_place_id>')
    def place(google_place_id):
        place = Place.query.filter_by(google_place_id=google_place_id).first()
        if not place:
            details = google_place_details(google_place_id)
            if not details:
                abort(404)
            place = get_or_create_place(details)

        if not place.photo_reference:
            details = google_place_details(google_place_id)
            if details and details.get('photos'):
                place.photo_reference = details['photos'][0].get('photo_reference', '')
                db.session.commit()

        vibes = place.vibe_checks.order_by(VibeCheck.created_at.desc()).all()
        is_saved = False
        if current_user.is_authenticated:
            is_saved = SavedPlace.query.filter_by(
                user_id=current_user.id, place_id=place.id).first() is not None

        photo_url = google_photo_url(place.photo_reference, 800)

        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        dist = None
        if lat and lng and place.latitude and place.longitude:
            dist = haversine(lat, lng, place.latitude, place.longitude)

        return render_template('place.html', place=place, vibes=vibes,
                               is_saved=is_saved, photo_url=photo_url,
                               dist=dist, lat=lat, lng=lng)

    @app.route('/vibe_check/<google_place_id>', methods=['GET', 'POST'])
    @login_required
    def vibe_check(google_place_id):
        if current_user.is_banned:
            flash('Your account has been banned.', 'error')
            return redirect(url_for('index'))

        place = Place.query.filter_by(google_place_id=google_place_id).first()
        if not place:
            abort(404)

        tags = VibeTag.query.order_by(VibeTag.name).all()

        if request.method == 'POST':
            photo_files = []
            for i in range(4):
                photo = request.files.get(f'photo_{i}')
                camera = request.files.get(f'camera_photo_{i}')
                actual = photo or camera
                if actual and actual.filename and allowed_file(actual.filename):
                    photo_files.append(actual)

            if not photo_files:
                flash('NO PHOTO = NO VIBE CHECK 👀 Upload a photo!', 'error')
                return redirect(url_for('vibe_check', google_place_id=google_place_id))

            rating = request.form.get('rating', type=int)
            if not rating or rating < 1 or rating > 5:
                flash('Rate the vibe 1-5 stars!', 'error')
                return redirect(url_for('vibe_check', google_place_id=google_place_id))

            review_text = request.form.get('review_text', '')[:300]
            selected_tags = request.form.getlist('tags')

            lat = request.form.get('latitude', type=float)
            lng = request.form.get('longitude', type=float)
            loc_verified = False

            if lat and lng and place.latitude and place.longitude:
                dist = haversine(lat, lng, place.latitude, place.longitude)
                if dist <= app.config['LOCATION_VERIFY_RADIUS']:
                    loc_verified = True

            vc = VibeCheck(
                user_id=current_user.id,
                place_id=place.id,
                rating=rating,
                review_text=review_text,
                latitude=lat,
                longitude=lng,
                location_verified=loc_verified,
            )
            db.session.add(vc)
            db.session.flush()

            for pf in photo_files:
                result = upload_to_cloudinary(pf, 'vibes')
                if result:
                    vp = VibePhoto(
                        vibe_check_id=vc.id,
                        filename=result['url'],
                        public_id=result['public_id']
                    )
                    db.session.add(vp)

            for tid in selected_tags:
                vct = VibeCheckTag(vibe_check_id=vc.id, tag_id=int(tid))
                db.session.add(vct)

            db.session.commit()
            send_telegram_notification(vc, place)
            flash('VIBE CHECK POSTED 🔥', 'success')
            return redirect(url_for('place', google_place_id=google_place_id))

        return render_template('vibe_check.html', place=place, tags=tags)

    @app.route('/explore')
    def explore():
        cat = request.args.get('category', '').strip()
        sort = request.args.get('sort', 'vibe')
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)

        query = Place.query.filter(Place.vibe_checks.any())

        if cat in CATEGORY_MAP:
            query = query.filter_by(category=cat)

        if sort == 'vibe':
            places = query.all()
            places.sort(key=lambda p: p.vibe_score or 0, reverse=True)
        elif sort == 'checks':
            vc_count_sub = db.session.query(
                VibeCheck.place_id,
                func.count(VibeCheck.id).label('cnt')
            ).group_by(VibeCheck.place_id).subquery()

            places = db.session.query(Place).join(
                vc_count_sub, Place.id == vc_count_sub.c.place_id
            ).order_by(vc_count_sub.c.cnt.desc()).all()
        elif sort == 'nearest' and lat and lng:
            places = query.all()
            places.sort(key=lambda p: haversine(lat, lng, p.latitude or 0, p.longitude or 0))
        elif sort == 'recent':
            subq = db.session.query(
                VibeCheck.place_id,
                func.max(VibeCheck.created_at).label('latest')
            ).group_by(VibeCheck.place_id).subquery()
            places = (query.outerjoin(subq, Place.id == subq.c.place_id)
                      .order_by(func.coalesce(subq.c.latest, Place.created_at).desc())
                      .all())
        else:
            places = query.all()

        return render_template('explore.html', places=places, cat=cat,
                               sort=sort, lat=lat, lng=lng)

    @app.route('/save/<google_place_id>')
    @login_required
    def save_place(google_place_id):
        place = Place.query.filter_by(google_place_id=google_place_id).first()
        if not place:
            abort(404)
        existing = SavedPlace.query.filter_by(
            user_id=current_user.id, place_id=place.id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            flash('Removed from saved', 'info')
        else:
            sp = SavedPlace(user_id=current_user.id, place_id=place.id)
            db.session.add(sp)
            db.session.commit()
            flash('Saved ❤️', 'success')
        return redirect(request.referrer or url_for('index'))

    @app.route('/saved')
    @login_required
    def saved():
        saved = SavedPlace.query.filter_by(user_id=current_user.id)\
            .order_by(SavedPlace.created_at.desc()).all()
        return render_template('saved.html', saved=saved)

    @app.route('/profile/<username>')
    def profile(username):
        user = User.query.filter_by(username=username).first_or_404()
        vibes = VibeCheck.query.filter_by(user_id=user.id)\
            .order_by(VibeCheck.created_at.desc()).all()
        places_checked = db.session.query(Place.id).join(VibeCheck)\
            .filter(VibeCheck.user_id == user.id).distinct().count()
        cat_counts = {}
        for v in vibes:
            p = Place.query.get(v.place_id)
            if p:
                cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
        fav_cat = max(cat_counts, key=cat_counts.get) if cat_counts else None
        return render_template('profile.html', user=user, vibes=vibes,
                               places_checked=places_checked, fav_cat=fav_cat)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            user = User.query.filter_by(username=username).first()
            if not user or not user.check_password(password):
                flash('Invalid username or password', 'error')
                return redirect(url_for('login'))
            if user.is_banned:
                flash('Account banned.', 'error')
                return redirect(url_for('login'))
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm = request.form.get('confirm_password', '')

            if not username or len(username) < 3:
                flash('Username must be at least 3 characters', 'error')
                return redirect(url_for('register'))
            if not email or '@' not in email:
                flash('Valid email required', 'error')
                return redirect(url_for('register'))
            if len(password) < 6:
                flash('Password must be at least 6 characters', 'error')
                return redirect(url_for('register'))
            if password != confirm:
                flash('Passwords do not match', 'error')
                return redirect(url_for('register'))
            if User.query.filter_by(username=username).first():
                flash('Username taken', 'error')
                return redirect(url_for('register'))
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return redirect(url_for('register'))

            user = User(username=username, email=email)
            user.set_password(password)

            photo = request.files.get('profile_photo')
            if photo and photo.filename and allowed_file(photo.filename):
                result = upload_to_cloudinary(photo, 'profiles')
                if result:
                    user.profile_photo = result['url']

            db.session.add(user)
            db.session.commit()
            flash('Account created! Login now 🔥', 'success')
            return redirect(url_for('login'))
        return render_template('register.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/report/<int:vibe_check_id>', methods=['POST'])
    @login_required
    def report(vibe_check_id):
        vc = VibeCheck.query.get_or_404(vibe_check_id)
        reason = request.form.get('reason', '').strip()
        valid_reasons = ['Fake review', 'Wrong place', 'Inappropriate photo',
                         'Spam', 'Offensive content', 'Other']
        if reason not in valid_reasons:
            flash('Invalid report reason', 'error')
            return redirect(request.referrer or url_for('index'))
        existing = Report.query.filter_by(
            vibe_check_id=vc.id, user_id=current_user.id).first()
        if existing:
            flash('Already reported', 'info')
            return redirect(request.referrer or url_for('index'))
        report_obj = Report(vibe_check_id=vc.id, user_id=current_user.id, reason=reason)
        db.session.add(report_obj)
        db.session.commit()
        flash('Reported. We\'ll look into it.', 'info')
        return redirect(request.referrer or url_for('index'))

    # ---- Admin ----

    @app.route('/admin')
    @login_required
    def admin():
        if not current_user.is_admin:
            abort(403)
        users = User.query.order_by(User.created_at.desc()).all()
        vibes = VibeCheck.query.order_by(VibeCheck.created_at.desc()).all()
        reports = Report.query.filter_by(status='pending').order_by(Report.created_at.desc()).all()
        total_users = User.query.count()
        total_vibes = VibeCheck.query.count()
        total_photos = VibePhoto.query.count()
        return render_template('admin.html', users=users, vibes=vibes, reports=reports,
                               total_users=total_users, total_vibes=total_vibes,
                               total_photos=total_photos)

    @app.route('/admin/delete_vibe/<int:vid>')
    @login_required
    def admin_delete_vibe(vid):
        if not current_user.is_admin:
            abort(403)
        vc = VibeCheck.query.get_or_404(vid)
        
        for p in vc.photos:
            if p.public_id:
                delete_from_cloudinary(p.public_id)
            db.session.delete(p)
        
        VibeCheckTag.query.filter_by(vibe_check_id=vid).delete()
        Report.query.filter_by(vibe_check_id=vid).delete()
        db.session.delete(vc)
        db.session.commit()
        flash('Vibe Check deleted', 'info')
        return redirect(url_for('admin'))

    @app.route('/admin/ban_user/<int:uid>')
    @login_required
    def admin_ban_user(uid):
        if not current_user.is_admin:
            abort(403)
        user = User.query.get_or_404(uid)
        user.is_banned = not user.is_banned
        db.session.commit()
        flash(f"User {'banned' if user.is_banned else 'unbanned'}", 'info')
        return redirect(url_for('admin'))

    @app.route('/admin/delete_report/<int:rid>')
    @login_required
    def admin_delete_report(rid):
        if not current_user.is_admin:
            abort(403)
        report_obj = Report.query.get_or_404(rid)
        report_obj.status = 'resolved'
        db.session.commit()
        flash('Report resolved', 'info')
        return redirect(url_for('admin'))

    # ---- API endpoints for JS ----

    @app.route('/api/search')
    def api_search():
        q = request.args.get('q', '').strip()
        cat = request.args.get('category', '').strip()
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)

        if not q and not cat:
            return jsonify([])

        if cat in CATEGORY_MAP:
            ci = CATEGORY_MAP[cat]
            query_str = ci.get('query', ci.get('label', ''))
            if q:
                query_str = f"{q} {query_str}"
            gresults, _ = google_search(query_str, lat, lng, cat)
        elif q:
            gresults, _ = google_search(q, lat, lng)
        else:
            gresults = []

        output = []
        for gr in gresults[:20]:
            place = get_or_create_place(gr, cat if cat in CATEGORY_MAP else None)
            dist = 0
            if lat and lng and place.latitude and place.longitude:
                dist = haversine(lat, lng, place.latitude, place.longitude)
            output.append({
                'google_place_id': place.google_place_id,
                'name': place.name,
                'category': place.category,
                'address': place.address,
                'google_rating': place.google_rating,
                'vibe_score': place.vibe_score,
                'vibe_check_count': place.vibe_check_count,
                'distance': dist,
                'photo_url': google_photo_url(place.photo_reference, 400),
            })
        return jsonify(output)

    # ---- Error handlers ----

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    # ---- Init ----

    with app.app_context():
        db.create_all()
        seed_tags()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)