import os
import sys
import tempfile
import io
from unittest import TestCase

# Ensure the app module can be found
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, User, Place, VibeCheck, VibeTag, VibeCheckTag, SavedPlace, Report


class VibeMapTestCase(TestCase):

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        config = {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{self.db_path}',
            'WTF_CSRF_ENABLED': False,
            'GOOGLE_PLACES_API_KEY': 'test-key',
            'SECRET_KEY': 'test-secret',
            'UPLOAD_FOLDER': tempfile.mkdtemp(),
        }
        self.app = create_app()
        self.app.config.update(config)

        with self.app.app_context():
            db.create_all()

        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _create_user(self, username='testuser', email='test@test.com', password='password123'):
        with self.app.app_context():
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return user.id

    def _create_place(self, name='Test Place', category='cafe', gpid='test_gpid_123'):
        with self.app.app_context():
            place = Place(
                google_place_id=gpid, name=name, category=category,
                address='Test Address', latitude=26.9124, longitude=75.7873,
                google_rating=4.2
            )
            db.session.add(place)
            db.session.commit()
            return place.id

    def _create_vibe_check(self, user_id, place_id, rating=5, photo='test.jpg'):
        with self.app.app_context():
            # Create a minimal test image file
            from PIL import Image as PILImage
            img = PILImage.new('RGB', (100, 100), color='red')
            buf = io.BytesIO()
            img.save(buf, format='JPEG')
            buf.seek(0)

            fname = f"test_{user_id}_{place_id}.jpg"
            filepath = os.path.join(self.app.config['UPLOAD_FOLDER'], 'vibes', fname)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(buf.read())

            vc = VibeCheck(
                user_id=user_id, place_id=place_id, rating=rating,
                review_text='Great vibe!', photo_filename=f'vibes/{fname}',
                location_verified=True
            )
            db.session.add(vc)
            db.session.commit()
            return vc.id

    # ---- Registration Tests ----

    def test_register_page_loads(self):
        resp = self.client.get('/register')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'VIBE MAP', resp.data)

    def test_register_success(self):
        resp = self.client.post('/register', data={
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Account created', resp.data)

    def test_register_short_username(self):
        resp = self.client.post('/register', data={
            'username': 'ab',
            'email': 'ab@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        self.assertIn(b'at least 3 characters', resp.data)

    def test_register_password_mismatch(self):
        resp = self.client.post('/register', data={
            'username': 'testuser2',
            'email': 'test2@test.com',
            'password': 'password123',
            'confirm_password': 'different',
        }, follow_redirects=True)
        self.assertIn(b'do not match', resp.data)

    def test_register_duplicate_username(self):
        self._create_user('taken', 'taken@test.com')
        resp = self.client.post('/register', data={
            'username': 'taken',
            'email': 'other@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        self.assertIn(b'taken', resp.data)

    # ---- Login Tests ----

    def test_login_page_loads(self):
        resp = self.client.get('/login')
        self.assertEqual(resp.status_code, 200)

    def test_login_success(self):
        self._create_user()
        resp = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'password123',
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_login_invalid_password(self):
        self._create_user()
        resp = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpassword',
        }, follow_redirects=True)
        self.assertIn(b'Invalid', resp.data)

    def test_login_invalid_username(self):
        resp = self.client.post('/login', data={
            'username': 'nonexistent',
            'password': 'password123',
        }, follow_redirects=True)
        self.assertIn(b'Invalid', resp.data)

    # ---- Auth Protection Tests ----

    def test_vibe_check_requires_login(self):
        self._create_place()
        resp = self.client.get('/vibe_check/test_gpid_123')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.headers.get('Location', ''))

    def test_saved_requires_login(self):
        resp = self.client.get('/saved')
        self.assertEqual(resp.status_code, 302)

    # ---- Place Tests ----

    def test_place_page_404_without_google_data(self):
        resp = self.client.get('/place/nonexistent_place_id')
        self.assertEqual(resp.status_code, 404)

    def test_place_page_loads(self):
        self._create_place()
        resp = self.client.get('/place/test_gpid_123')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Test Place', resp.data)

    # ---- Category Tests ----

    def test_categories_are_correct(self):
        with self.app.app_context():
            from app import CATEGORY_MAP
            self.assertIn('chai', CATEGORY_MAP)
            self.assertIn('cafe', CATEGORY_MAP)
            self.assertIn('restaurant', CATEGORY_MAP)
            self.assertIn('hangout', CATEGORY_MAP)
            self.assertEqual(len(CATEGORY_MAP), 4)

    # ---- Vibe Check Tests ----

    def test_vibe_check_requires_photo(self):
        uid = self._create_user()
        pid = self._create_place()
        self.client.post('/login', data={
            'username': 'testuser', 'password': 'password123'
        })
        resp = self.client.post('/vibe_check/test_gpid_123', data={
            'rating': '5',
            'review_text': 'Nice place!',
        }, follow_redirects=True)
        self.assertIn(b'NO PHOTO', resp.data)

    def test_vibe_check_requires_rating(self):
        uid = self._create_user()
        pid = self._create_place()
        self.client.post('/login', data={
            'username': 'testuser', 'password': 'password123'
        })

        # Create a test image
        from PIL import Image as PILImage
        img = PILImage.new('RGB', (100, 100), color='blue')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)

        resp = self.client.post('/vibe_check/test_gpid_123', data={
            'photo': (buf, 'test.jpg'),
            'rating': '',
            'review_text': 'Nice place!',
        }, follow_redirects=True)
        self.assertIn(b'Rate the vibe', resp.data)

    def test_vibe_check_success(self):
        uid = self._create_user()
        pid = self._create_place()
        self.client.post('/login', data={
            'username': 'testuser', 'password': 'password123'
        })

        from PIL import Image as PILImage
        img = PILImage.new('RGB', (200, 200), color='green')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)

        resp = self.client.post('/vibe_check/test_gpid_123', data={
            'photo': (buf, 'test_vibe.jpg'),
            'rating': '4',
            'review_text': 'Cool vibes here!',
            'latitude': '26.9124',
            'longitude': '75.7873',
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'VIBE CHECK POSTED', resp.data)

    def test_invalid_photo_type_rejected(self):
        uid = self._create_user()
        pid = self._create_place()
        self.client.post('/login', data={
            'username': 'testuser', 'password': 'password123'
        })

        buf = io.BytesIO(b'not an image')
        resp = self.client.post('/vibe_check/test_gpid_123', data={
            'photo': (buf, 'test.gif'),
            'rating': '5',
        }, follow_redirects=True)
        self.assertIn(b'Invalid file type', resp.data)

    # ---- Vibe Score Tests ----

    def test_vibe_score_calculation(self):
        uid = self._create_user()
        pid = self._create_place()

        # Create multiple vibe checks
        for r in [5, 5, 4, 5, 3]:
            self._create_vibe_check(uid, pid, rating=r)

        with self.app.app_context():
            place = Place.query.get(pid)
            score = place.vibe_score
            self.assertIsNotNone(score)
            self.assertGreater(score, 0)
            self.assertLessEqual(score, 100)

    def test_vibe_score_label_new(self):
        uid = self._create_user()
        pid = self._create_place()
        self._create_vibe_check(uid, pid)

        with self.app.app_context():
            place = Place.query.get(pid)
            self.assertEqual(place.vibe_score_label, 'NEW VIBE')

    def test_vibe_score_label_emerging(self):
        uid = self._create_user()
        pid = self._create_place()
        for _ in range(10):
            self._create_vibe_check(uid, pid)

        with self.app.app_context():
            place = Place.query.get(pid)
            self.assertEqual(place.vibe_score_label, 'EMERGING VIBE')

    def test_vibe_score_no_checks(self):
        pid = self._create_place()
        with self.app.app_context():
            place = Place.query.get(pid)
            self.assertIsNone(place.vibe_score)
            self.assertEqual(place.vibe_score_label, 'NO VIBES YET')

    # ---- Saved Places Tests ----

    def test_save_and_unsave_place(self):
        uid = self._create_user()
        pid = self._create_place()
        self.client.post('/login', data={
            'username': 'testuser', 'password': 'password123'
        })

        # Save
        resp = self.client.get('/save/test_gpid_123', follow_redirects=True)
        self.assertIn(b'Saved', resp.data)

        with self.app.app_context():
            self.assertIsNotNone(SavedPlace.query.filter_by(user_id=uid, place_id=pid).first())

        # Unsave
        resp = self.client.get('/save/test_gpid_123', follow_redirects=True)
        self.assertIn(b'Removed', resp.data)

        with self.app.app_context():
            self.assertIsNone(SavedPlace.query.filter_by(user_id=uid, place_id=pid).first())

    # ---- Report Tests ----

    def test_report_vibe_check(self):
        uid1 = self._create_user('reporter', 'reporter@test.com')
        uid2 = self._create_user('author', 'author@test.com', 'pass456')
        pid = self._create_place()
        vc_id = self._create_vibe_check(uid2, pid)

        self.client.post('/login', data={
            'username': 'reporter', 'password': 'password123'
        })

        resp = self.client.post(f'/report/{vc_id}', data={
            'reason': 'Fake review'
        }, follow_redirects=True)
        self.assertIn(b'Reported', resp.data)

        with self.app.app_context():
            self.assertIsNotNone(Report.query.filter_by(vibe_check_id=vc_id, user_id=uid1).first())

    def test_report_invalid_reason(self):
        uid1 = self._create_user('reporter2', 'reporter2@test.com')
        uid2 = self._create_user('author2', 'author2@test.com', 'pass456')
        pid = self._create_place(gpid='test_gpid_456')
        vc_id = self._create_vibe_check(uid2, pid)

        self.client.post('/login', data={
            'username': 'reporter2', 'password': 'password123'
        })

        resp = self.client.post(f'/report/{vc_id}', data={
            'reason': 'Invalid reason'
        }, follow_redirects=True)
        self.assertIn(b'Invalid report reason', resp.data)

    # ---- Admin Tests ----

    def test_admin_requires_admin(self):
        uid = self._create_user()
        self.client.post('/login', data={
            'username': 'testuser', 'password': 'password123'
        })
        resp = self.client.get('/admin')
        self.assertEqual(resp.status_code, 403)

    def test_admin_access(self):
        with self.app.app_context():
            user = User.query.filter_by(username='testuser').first()
            user.is_admin = True
            db.session.commit()

        self.client.post('/login', data={
            'username': 'testuser', 'password': 'password123'
        })
        resp = self.client.get('/admin')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'ADMIN PANEL', resp.data)

    def test_admin_delete_vibe(self):
        uid = self._create_user()
        pid = self._create_place()
        vc_id = self._create_vibe_check(uid, pid)

        with self.app.app_context():
            user = User.query.filter_by(username='testuser').first()
            user.is_admin = True
            db.session.commit()

        self.client.post('/login', data={
            'username': 'testuser', 'password': 'password123'
        })

        resp = self.client.get(f'/admin/delete_vibe/{vc_id}', follow_redirects=True)
        self.assertIn(b'deleted', resp.data.lower())

        with self.app.app_context():
            self.assertIsNone(VibeCheck.query.get(vc_id))

    def test_admin_ban_user(self):
        uid1 = self._create_user('admin_user', 'admin@test.com', 'adminpass')
        uid2 = self._create_user('ban_me', 'ban@test.com', 'banpass')

        with self.app.app_context():
            User.query.filter_by(id=uid1).first().is_admin = True
            db.session.commit()

        self.client.post('/login', data={
            'username': 'admin_user', 'password': 'adminpass'
        })

        self.client.get(f'/admin/ban_user/{uid2}', follow_redirects=True)
        with self.app.app_context():
            self.assertTrue(User.query.get(uid2).is_banned)

    # ---- Search Tests ----

    def test_search_page_loads(self):
        resp = self.client.get('/search')
        self.assertEqual(resp.status_code, 200)

    def test_search_with_query(self):
        resp = self.client.get('/search?q=chai+in+jaipur')
        self.assertEqual(resp.status_code, 200)

    def test_search_by_category(self):
        resp = self.client.get('/search?category=chai')
        self.assertEqual(resp.status_code, 200)

    # ---- Explore Tests ----

    def test_explore_page_loads(self):
        resp = self.client.get('/explore')
        self.assertEqual(resp.status_code, 200)

    # ---- Profile Tests ----

    def test_profile_page_loads(self):
        self._create_user()
        resp = self.client.get('/profile/testuser')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'testuser', resp.data)

    def test_profile_404(self):
        resp = self.client.get('/profile/nonexistent')
        self.assertEqual(resp.status_code, 404)

    # ---- Homepage Tests ----

    def test_homepage_loads(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'VIBE MAP', resp.data)
        self.assertIn(b'Check the vibe', resp.data)

    # ---- Logout Tests ----

    def test_logout(self):
        self._create_user()
        self.client.post('/login', data={
            'username': 'testuser', 'password': 'password123'
        })
        resp = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)


if __name__ == '__main__':
    import unittest
    unittest.main()