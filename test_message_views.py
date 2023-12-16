"""Message View tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, Message, User, Like

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

from app import app, CURR_USER_KEY

app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']

db.drop_all()
db.create_all()

app.config['WTF_CSRF_ENABLED'] = False


class MessageBaseViewTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        self.u1 = User.signup("u1", "u1@email.com", "password", None)
        self.u2 = User.signup("u2", "u2@email.com", "password", None)
        db.session.flush()

        self.m1 = Message(text="m1-text", user_id=self.u1.id)
        db.session.add_all([self.m1])
        db.session.commit()

class MessageAddViewTestCase(MessageBaseViewTestCase):
    def test_add_message_form(self):
        """Should load add message form"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            resp = c.get("/messages/new")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Comment for messages/create.html loaded.", html)

    def test_add_message(self):
        """Should be able to add messages"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            resp = c.post("/messages/new", data={"text": "Hello"})

            self.assertEqual(resp.status_code, 302)

            self.assertIsNotNone(Message
                                 .query
                                 .filter_by(text="Hello")
                                 .one_or_none())
            self.assertEqual(Message.query.count(), 2)
            self.assertNotIn(self.m1.id, self.u2.messages)

    def test_add_message_unauth(self):
        """Should not be able to add messages if not logged-in"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = None

            resp = c.post("/messages/new", follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 401)
            self.assertIn("Unauthorized", html)

class MessageDeleteViewTestCase(MessageBaseViewTestCase):

    def test_delete_message(self):
        """Should be able to delete messages"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            resp = c.post(f"/messages/{self.m1.id}/delete")

            self.assertEqual(resp.status_code, 302)

            self.assertIsNone(Message
                                 .query
                                 .filter_by(text=self.m1.text)
                                 .one_or_none())
            self.assertEqual(Message.query.count(), 0)

    def test_delete_message_unauth(self):
        """
        Should not be able to delete message if not original poster/authorized
        """

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2.id

            resp = c.post(
                f"/messages/{self.m1.id}/delete",
                follow_redirects=True
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 401)
            self.assertIn("Unauthorized", html)

class MessageShowViewTestCase(MessageBaseViewTestCase):

    def test_show_messages_with_delete_button_shown(self):
        """Should show message. Show delete button for own user's message"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            resp = c.get(
                f"/messages/{self.m1.id}",
                follow_redirects=True
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(self.m1.text, html)
            self.assertIn('Delete', html)
            self.assertIn("Comment for messages/show.html loaded.", html)

    def test_show_messages_without_delete_button_shown(self):
        """Should show message. Do not show delete button if not owned"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2.id

            resp = c.get(
                f"/messages/{self.m1.id}",
                follow_redirects=True
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(self.m1.text, html)
            self.assertNotIn('Delete', html)
            self.assertIn("Comment for messages/show.html loaded.", html)


    def test_show_messages_unauth(self):
        """Should not show message if unauthorized"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = None

            resp = c.get(
                f"/messages/{self.m1.id}",
                follow_redirects=True
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", html)
            self.assertNotIn("Comment for messages/show.html loaded.", html)

class MessageLikeViewTestCase(MessageBaseViewTestCase):

    def test_like_message(self):
        """Should be able to like a message"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2.id

            resp = c.post(f'/messages/{self.m1.id}/like')

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f'/messages/{self.m1.id}')

            self.assertIn(self.m1, self.u2.messages_liked)

            self.assertIsNotNone(Like
                                 .query
                                 .filter_by(message_id=self.m1.id)
                                 .one_or_none())
            self.assertEqual(Like.query.count(), 1)
            self.assertEqual(len(self.u2.messages_liked), 1)
            self.assertEqual(len(self.m1.liking_users), 1)

            resp = c.get(resp.location)
            html = resp.get_data(as_text=True)

            self.assertIn("bi-star-fill", html)

    def test_like_message_self(self):
        """Should not be able to like own message"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1.id

            resp = c.post(f'/messages/{self.m1.id}/like')

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f'/messages/{self.m1.id}')

            self.assertNotIn(self.m1, self.u1.messages_liked)

            self.assertIsNone(Like
                                 .query
                                 .filter_by(message_id=self.m1.id)
                                 .one_or_none())
            self.assertEqual(Like.query.count(), 0)
            self.assertNotEqual(len(self.u1.messages_liked), 1)
            self.assertNotEqual(len(self.m1.liking_users), 1)

            resp = c.get(resp.location)
            html = resp.get_data(as_text=True)

            self.assertIn("You cannot like your own Warble!", html)
            self.assertNotIn("bi-star-fill", html)

    def test_like_messages_unauth(self):
        """Should not be able to like if unauthorized"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = None

            resp = c.post(f'/messages/{self.m1.id}/like', follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 401)
            self.assertIn("Unauthorized", html)
            self.assertNotIn("bi-star", html)
            self.assertNotEqual(len(self.m1.liking_users), 1)

    def test_show_liked_messages(self):
        """Should show a user's liked messages"""

        self.u2.messages_liked.append(self.m1)
        db.session.commit()

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2.id

            resp = c.get(f'/users/{self.u2.id}/messages/liked')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(self.u1.username, html)
            self.assertIn(self.m1.text, html)
            self.assertIn('Comment for users/liked.html loaded', html)


    def test_show_liked_messages_unauth(self):
        """Should not show a user's liked messages if not logged in"""

        self.u2.messages_liked.append(self.m1)
        db.session.commit()

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = None

            resp = c.get(
                f'/users/{self.u2.id}/messages/liked',
                follow_redirects=True
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", html)
            self.assertNotIn(self.m1.text, html)
            self.assertNotIn('Comment for users/liked.html loaded', html)

class MessageUnlikeViewTestCase(MessageBaseViewTestCase):

    def test_unlike_message(self):
        """Should be able to unlike a message"""

        self.u2.messages_liked.append(self.m1)
        db.session.commit()

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2.id

            resp = c.post(f'/messages/{self.m1.id}/unlike')

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f'/messages/{self.m1.id}')

            self.assertNotIn(self.m1, self.u2.messages_liked)

            self.assertIsNone(Like
                                 .query
                                 .filter_by(message_id=self.m1.id)
                                 .one_or_none())
            self.assertNotEqual(Like.query.count(), 1)
            self.assertNotEqual(len(self.u2.messages_liked), 1)
            self.assertNotEqual(len(self.m1.liking_users), 1)

            resp = c.get(resp.location)
            html = resp.get_data(as_text=True)

            self.assertNotIn("bi-star-fill", html)

    def test_unlike_messages_not_liked(self):
        """Should stay unliked if unliked"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2.id

            resp = c.post(
                f'/messages/{self.m1.id}/unlike',
                follow_redirects=True
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("bi-star-fill", html)
            self.assertNotEqual(self.u2.messages_liked, 1)