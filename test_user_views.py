"""Message View tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app, CURR_USER_KEY

app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

# This is a bit of hack, but don't use Flask DebugToolbar

app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class UserBaseViewTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        self.u1 = User.signup("u1", "u1@email.com", "password", None)
        self.u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.commit()

    def tearDown(self):
        """Rollback any fouled transactions"""

        db.session.rollback()


class UserAddViewTestCase(UserBaseViewTestCase):

    def test_homepage_redirect_loggedin(self):
        """Should redirect to home if logged in."""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            resp = c.get('/')
            html = resp.text

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Comment for home.html loaded.', html)

    def test_homepage_redirect_anon(self):
        """Should redirect to home anon if not logged in."""

        with app.test_client() as c:
            resp = c.get('/')
            html = resp.text

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Comment for home-anon.html loaded.', html)

    def test_signup_form(self):
        """Should load signup form"""

        with app.test_client() as c:
            resp = c.get("/signup")
            html = resp.text

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Comment for users/signup.html loaded.', html)

    def test_signup_submit_ok(self):
        """Should sign up user and redirect to home"""

        with app.test_client() as c:
            resp = c.post(
                "/signup",
                data={
                    "username": "test",
                    "email": "test@email.com",
                    "password": "password",
                    "image_url": None
                    },
            )

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

            self.assertIsNotNone(User
                                 .query
                                 .filter_by(username="test")
                                 .one_or_none())

    def test_signup_submit_fail(self):
        """Should redirect back to form if username or email taken"""

        with app.test_client() as c:
            resp = c.post(
                "/signup",
                data={
                    "username": self.u1.username,
                    "email": self.u1.email,
                    "password": "password",
                    "image_url": None
                    },
                follow_redirects=True,
            )
            html = resp.text

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Comment for users/signup.html loaded.', html)
            self.assertIn("Username or email already taken", html)

