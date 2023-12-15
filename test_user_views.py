"""Message View tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_message_views.py


import os
from flask import session
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

        self.valid_password = "password"

        self.u1 = User.signup("u1", "u1@email.com", self.valid_password, None)
        self.u2 = User.signup("u2", "u2@email.com", self.valid_password, None)

        db.session.commit()

    def tearDown(self):
        """Rollback any fouled transactions"""

        db.session.rollback()

class UserHomeRedirectTestCase(UserBaseViewTestCase):

    def test_homepage_redirect_loggedin(self):
        """Should redirect to home if logged in."""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            resp = c.get('/')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Comment for home.html loaded.', html)

    def test_homepage_redirect_anon(self):
        """Should redirect to home anon if not logged in."""

        with app.test_client() as c:
            resp = c.get('/')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Comment for home-anon.html loaded.', html)


class UserAddViewTestCase(UserBaseViewTestCase):

    def test_signup_form(self):
        """Should load signup form"""

        with app.test_client() as c:
            resp = c.get("/signup")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Comment for users/signup.html loaded.', html)

    def test_signup_form_logged_in(self):
        """Should log you out if you load signup form while logged in"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id
            resp = c.get("/signup")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Comment for users/signup.html loaded.', html)
            self.assertEqual(session.get(CURR_USER_KEY), None)

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
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Comment for users/signup.html loaded.', html)
            self.assertIn("Username or email already taken", html)


class UserLoginViewTestCase(UserBaseViewTestCase):

    def test_login_form(self):
        """Should load login form"""

        with app.test_client() as c:
            resp = c.get("/login")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Comment for users/login.html loaded.', html)

    def test_login_ok(self):
        """Should sign up user and redirect to home"""

        with app.test_client() as client:
            resp = client.post(
                "/login",
                data={
                    "username": self.u1.username,
                    "password": self.valid_password,
                    }
            )
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")
            self.assertEqual(session.get(CURR_USER_KEY), self.u1.id)

    def test_login_bad(self):
        """Should redirect back to form if username or email taken"""

        with app.test_client() as client:
            resp = client.post(
                "/login",
                data={
                    "username": self.u1.username,
                    "password": "wrong-wrong",
                }
            )
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Invalid credentials", html)
            self.assertEqual(session.get(CURR_USER_KEY), None)

    def test_logout(self):
        """Should log out user and redirect to homepage"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id
            resp = c.post(
                "/logout"
            )

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")
            self.assertEqual(session.get(CURR_USER_KEY), None)

            resp = c.get(
                resp.location,
                follow_redirects=True,
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('User logged out!', html)


class UserListViewTestCase(UserBaseViewTestCase):

    def test_list_users(self):
        """Should list warbler users if logged-in"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id
            resp = c.get('/users')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Comment for users/index.html loaded.", html)
            self.assertEqual(session.get(CURR_USER_KEY), self.u1.id)

    def test_list_users_search_found(self):
        """Should find a searched for user"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            resp = c.get(f'/users?q={self.u2.username}')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(self.u2.username, html)

    def test_list_users_search_not_found(self):
        """Should not find user with search criteria that doesn't match"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            resp = c.get(f'/users?q={self.u1.username}')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn(self.u2.username, html)


class UserProfileViewTestCase(UserBaseViewTestCase):

    def test_show_user(self):
        """Should show data about a user if logged in"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id
            resp = c.get(
                f"/users/{self.u1.id}",
            )

            html = resp.get_data(as_text=True)

            self.assertIn("Comment for users/show.html loaded.", html)
            self.assertIn(self.u1.username, html)

    def test_show_user_unauth(self):
        """Should not allow unauth user"""

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = None
            resp = client.get(
                f"/users/{self.u1.id}",
            )

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/")

            resp = client.get(
                resp.location,
                follow_redirects=True,
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)

    def test_delete_user(self):
        """Should be able to delete user"""

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            resp = client.post(
                "/users/delete",
            )

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/signup")
            self.assertEqual(session.get(CURR_USER_KEY), None)

            resp = client.get(resp.location)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f"Deleted {self.u1.username}!", html)


    # def test_remove_user_unauth(self):
    #     with app.test_client() as client:
    #         with client.session_transaction() as sess:
    #             sess["username"] = "wrong"
    #         resp = client.post(
    #             "/users/user-1/delete",
    #         )
    #         self.assertEqual(resp.status_code, 401)

    # def test_remove_user_404(self):
    #     with app.test_client() as client:
    #         with client.session_transaction() as sess:
    #             sess["username"] = "wrong"
    #         resp = client.post(
    #             "/users/wrong/delete",
    #         )
    #         self.assertEqual(resp.status_code, 404)
