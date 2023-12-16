import os
from unittest import TestCase

from models import db, User, Message

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"


from app import app

db.drop_all()
db.create_all()


class MessageModelTestCase(TestCase):
    def setUp(self):
        Message.query.delete()
        User.query.delete()

        self.valid_password = "password"

        u1 = User.signup("u1", "u1@email.com", self.valid_password, None)
        u2 = User.signup("u2", "u2@email.com", self.valid_password, None)
        m1 = Message(text="This is example message")
        u1.messages.append(m1)

        db.session.commit()
        self.u1_id = u1.id
        self.u2_id = u2.id
        self.u1 = u1
        self.u2 = u2
        self.m1 = m1

    def tearDown(self):
        db.session.rollback()


    def test_message_model(self):
        """Test that a message is created and linked to a user"""

        # User should have one messages & no followers
        self.assertEqual(len(self.u1.messages), 1)
        self.assertIn(self.m1, self.u1.messages)
        self.assertEqual(len(self.u1.followers), 0)

    def test_is_liked_by(self):
        """Test that a message (when liked) is added to users message's liked"""

        m2 = Message(text="Example m2")
        self.u2.messages.append(m2)
        db.session.commit()

        self.u1.messages_liked.append(m2)

        self.assertTrue(self.u1.is_liked_by(m2))
        self.assertFalse(self.u2.is_liked_by(m2))




