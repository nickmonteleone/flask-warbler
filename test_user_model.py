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
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

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


    def test_invalid_signup(self):

        self.assertRaises(IntegrityError,
            User.signup(
                        "u1",
                        "u4@gmail.com",
                        "password",
                        None
            ))


# def signup(cls, username, email, password, image_url=DEFAULT_IMAGE_URL):
#         """Sign up user.

#         Hashes password and adds user to session.
#         """

#         hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

#         user = User(
#             username=username,
#             email=email,
#             password=hashed_pwd,
#             image_url=image_url,
#         )

#         db.session.add(user)
#         return user

# Does User.signup successfully create a new user given valid credentials?
# Does User.signup fail to create a new user if any of the validations (eg uniqueness, non-nullable fields) fail?




    # def test_register(self):
    #     User.register("uname", "pwd", "First", "Last", "e@e.com")
    #     db.session.commit()

    #     u = db.session.get(User, "uname")
    #     self.assertTrue(bcrypt.check_password_hash(u.password, "pwd"))

    # def test_auth_ok(self):
    #     u = db.session.get(User, "user-1")
    #     self.assertEqual(User.authenticate("user-1", "password"), u)

    # def test_auth_fail_no_user(self):
    #     self.assertFalse(User.authenticate("user-X", "password"))

    # def test_auth_ok_wrong_pwd(self):
    #     u = db.session.get(User, "user-1")
    #     self.assertFalse(User.authenticate("user-1", "wrong"))


# Does User.authenticate successfully return a user when given a valid username and password?
# Does User.authenticate fail to return a user when the username is invalid?
# Does User.authenticate fail to return a user when the password is invalid