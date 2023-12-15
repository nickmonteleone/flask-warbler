"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError

from models import db, User, Message, Follow

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()


class UserModelTestCase(TestCase):
    def setUp(self):
        Message.query.delete()
        User.query.delete()

        self.valid_password = "password"

        u1 = User.signup("u1", "u1@email.com", self.valid_password, None)
        u2 = User.signup("u2", "u2@email.com", self.valid_password, None)

        db.session.commit()
        self.u1_id = u1.id
        self.u2_id = u2.id
        self.u1 = u1
        self.u2 = u2

    def tearDown(self):
        db.session.rollback()

    def test_user_model(self):
        u1 = User.query.get(self.u1_id)

        # User should have no messages & no followers
        self.assertEqual(len(u1.messages), 0)
        self.assertEqual(len(u1.followers), 0)

    def test_is_following(self):

        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u1.is_following(self.u2))
        self.assertFalse(self.u2.is_following(self.u1))

    def test_is_followed_by(self):

        self.u1.followers.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u1.is_followed_by(self.u2))
        self.assertFalse(self.u2.is_followed_by(self.u1))

    def test_valid_signup(self):

        u3 = User.signup("u3", "u3@email.com", "password", None)

        self.assertIsNotNone(User
                             .query
                             .filter_by(username=u3.username)
                             .one_or_none())

    def test_invalid_signup_username(self):
        """Should not allow sign up for taken username"""

        try:
            u4 = User.signup(self.u1.username, "u4@gmail.com","password",None)
            db.session.commit()

        except IntegrityError:
            u4 = 'username already taken'

        self.assertEqual(u4, 'username already taken')

    def test_invalid_signup_email(self):
        """Should not allow sign up for taken email"""

        try:
            u4 = User.signup('u4', self.u1.email,"password",None)
            db.session.commit()

        except IntegrityError:
            u4 = 'email already taken'

        self.assertEqual(u4, 'email already taken')

    def test_auth_ok(self):
        """Should authenticate and return user for valid creds"""

        u1_auth = User.authenticate(self.u1.username, self.valid_password)
        self.assertEqual(u1_auth, self.u1)

    def test_auth_fail_no_user(self):
        """Should not auth for invalid username"""

        self.assertFalse(User.authenticate("XXXXXX", self.valid_password))

    def test_auth_ok_wrong_pwd(self):
        """Should not auth for invalid pw"""

        self.assertFalse(User.authenticate(self.u1.username, 'XXXXXXX'))