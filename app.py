import os
from dotenv import load_dotenv

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Unauthorized

from forms import (UserAddForm,
                LoginForm, MessageForm, CSRFProtectForm, UserEditForm)
from models import db, connect_db, User, Message

load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# User signup/login/logout

@app.before_request
def add_to_g():
    """Add parameters to Flask global before each request."""

    add_user_to_g()
    add_csrf_form_to_g()

def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None

def add_csrf_form_to_g():
    """Add csrf form to Flask global."""

    g.csrf_form = CSRFProtectForm()


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Log out user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    do_logout()

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username or email already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login and redirect to homepage on success."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(
            form.username.data,
            form.password.data,
        )

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.post('/logout')
def logout():
    """Handle logout of user and redirect to homepage."""

    form = g.csrf_form

    if not form.validate_on_submit() or not g.user:
        raise Unauthorized()

    do_logout()
    flash('User logged out!', 'success')
    return redirect("/")


##############################################################################
# General user routes:

@app.get('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.get('/users/<int:user_id>')
def show_user(user_id):
    """Show user profile."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    return render_template('users/show.html', user=user)


@app.get('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.get('/users/<int:user_id>/followers')
def show_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.get('/users/<int:user_id>/messages/liked')
def show_liked_messages(user_id):
    """Show liked messages"""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    messages_ids_to_show = [message.id for  message in user.messages_liked]

    messages = (Message
                .query
                .filter(Message.id.in_(messages_ids_to_show))
                .order_by(Message.timestamp.desc())
                .all())

    return render_template('/users/liked.html', user=user, messages=messages)


@app.post('/users/follow/<int:follow_id>')
def start_following(follow_id):
    """Add a follow for the currently-logged-in user.

    Redirect to following page for the current user.
    """

    form = g.csrf_form

    if not form.validate_on_submit() or not g.user:
        raise Unauthorized()

    followed_user = User.query.get_or_404(follow_id)

    if g.user.id == follow_id:
        flash("You cannot follow yourself!", "danger")

    elif followed_user not in g.user.following:
        g.user.following.append(followed_user)
        db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.post('/users/stop-following/<int:follow_id>')
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user.

    Redirect to following page for the current user.
    """

    form = g.csrf_form

    if not form.validate_on_submit() or not g.user:
        raise Unauthorized()

    followed_user = User.query.get_or_404(follow_id)

    if followed_user in g.user.following:
        g.user.following.remove(followed_user)
        db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def update_profile():
    """Update profile for current user."""

    if not g.user:
        raise Unauthorized()

    form = UserEditForm(obj=g.user)

    if form.validate_on_submit() and g.user:

        user = User.authenticate(
            g.user.username,
            form.password.data,
        )

        if user:

            username_check = (user.username != form.username.data and
                User.query.filter_by(username=form.username.data)
                .one_or_none())

            email_check = (user.email != form.email.data and
                User.query.filter_by(email=form.email.data)
                .one_or_none())

            if username_check or email_check:

                if username_check:
                    form.username.errors = ['Username already taken!']

                if email_check:
                    form.email.errors = ['Email already taken!']

            else:

                user.username = form.username.data
                user.email = form.email.data
                user.location = form.location.data
                user.bio = form.bio.data

                user.image_url = (form.image_url.data
                    or User.image_url.default.arg)
                user.header_image_url = (form.header_image_url.data
                    or User.header_image_url.default.arg)

                db.session.commit()
                flash(f"Updated {g.user.username}!", "success")
                return redirect(f"/users/{g.user.id}")

        else:

            form.password.errors = ["Incorrect password."]

    return render_template('/users/edit.html', form=form)


@app.post('/users/delete')
def delete_user():
    """Delete user.

    Redirect to signup page.
    """

    form = g.csrf_form

    if not form.validate_on_submit() or not g.user:
        raise Unauthorized()

    do_logout()

    for message in g.user.messages:
        db.session.delete(message)

    db.session.delete(g.user)
    db.session.commit()

    flash(f"Deleted {g.user.username}!", "success")

    return redirect("/signup")



##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def add_message():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        raise Unauthorized()

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/create.html', form=form)


@app.get('/messages/<int:message_id>')
def show_message(message_id):
    """Show a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get_or_404(message_id)
    return render_template('messages/show.html', message=msg)


@app.post('/messages/<int:message_id>/delete')
def delete_message(message_id):
    """Delete a message.

    Check that this message was written by the current user.
    Redirect to user page on success.
    """

    form = g.csrf_form

    if not form.validate_on_submit() or not g.user:
        raise Unauthorized()

    msg = Message.query.get_or_404(message_id)

    if msg.user_id != g.user.id:
        raise Unauthorized()

    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


@app.post('/messages/<int:message_id>/like')
def like_message(message_id):
    """Add a like to a message for the currently-logged-in user.

    Redirect to the current message.
    """

    form = g.csrf_form

    if not form.validate_on_submit() or not g.user:
        raise Unauthorized()

    message_to_like = Message.query.get_or_404(message_id)

    # like button hidden for own messages, but also catching here
    if g.user.id == message_to_like.user_id:
        flash("You cannot like your own Warble!", "danger")

    elif message_to_like not in g.user.messages_liked:
        g.user.messages_liked.append(message_to_like)
        db.session.commit()

    return redirect(
        request.form.get('referring_page', f'/messages/{message_id}'))


@app.post('/messages/<int:message_id>/unlike')
def unlike_message(message_id):
    """Have currently-logged-in-user unlike a selected message.

    Redirect to the current message.
    """

    form = g.csrf_form

    if not form.validate_on_submit() or not g.user:
        raise Unauthorized()

    message_to_unlike = Message.query.get_or_404(message_id)

    if message_to_unlike in g.user.messages_liked:
        g.user.messages_liked.remove(message_to_unlike)
        db.session.commit()

    return redirect(
        request.form.get(
            'referring_page',
            f'/messages/{message_id}'
        )
    )


##############################################################################
# Homepage and error pages


@app.get('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of self & followed_users
    """

    if g.user:

        user_ids_to_show = [user.id for user in g.user.following] + [g.user.id]

        messages = (Message
                    .query
                    .filter(Message.user_id.in_(user_ids_to_show))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        return render_template('home.html', messages=messages)

    else:
        return render_template('home-anon.html')


@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response
