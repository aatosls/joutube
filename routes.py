from app import app
from flask import render_template, request, redirect, session
from werkzeug.security import check_password_hash, generate_password_hash

import db, helpers

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        search_term = request.form["search"]
        if len(search_term) == 0:
            return redirect("/")
        thumbnails = helpers.search_by_title(search_term)
    else:
        thumbnails = db.select_thumbnails_new(100)

    messages = db.select_messages(100)
    return render_template("index.html", videos=thumbnails, messages=messages)

@app.route("/signup")
def signup_initial():
    return render_template("signup.html")

@app.route("/signup", methods=["POST"])
def signup():
    username = request.form["username"]
    password1 = request.form["password1"]
    password2 = request.form["password2"]

    message = ""
    accept_input = True

    if db.select_userid(username):
        message += "Username is already taken\n"
        accept_input = False
    if len(username) < 3:
        message += "Select username that is at least 3 characters\n"
        accept_input = False
    if len(password1) < 5 or len(password2) < 5:
        message += "Password must be at least 5 characters long\n"
        accept_input = False
    if password1 != password2:
        message += "Passwords do not match\n"
        accept_input = False

    if accept_input:
        hash_value = generate_password_hash(password1)
        db.insert_user(username, hash_value)
        session["username"] = username
        session["userid"] = db.select_userid(username)
        return redirect("/")
    else:
        return render_template("signup.html", username=username, message=message)

@app.route("/login")
def login_initial():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]

    message = ""
    accept_input = True

    userid = db.select_userid(username)
    if not userid or not check_password_hash(db.select_password_by_username(username), password):
        message += "Incorrect username or password"
        accept_input = False

    if accept_input:
        session["username"] = username
        session["userid"] = userid
        return redirect("/")
    else:
        return render_template("login.html", username=username, message=message)

@app.route("/logout")
def logout():
    del session["username"]
    del session["userid"]
    return redirect("/")

@app.route("/video/<int:video_id>")
def video(video_id):
    if not db.video_exists(video_id): return "This video does not exist :/"

    if "viewed_videos" not in session.keys():
        session["viewed_videos"] = []

    if video_id not in session["viewed_videos"]:
        viewed = session["viewed_videos"]
        viewed.append(video_id)
        session["viewed_videos"] = viewed
        db.increment_viewcount(video_id)

    video = db.select_video(video_id)
    comments = db.select_comments_new(video_id, 100)

    logged_in = "username" in session.keys()

    return render_template("video.html", video=video, comments=comments, logged_in=logged_in)

@app.route("/video/<int:video_id>", methods=["POST"])
def submit_comment(video_id):
    comment = request.form["comment"]

    if len(comment) != 0:
        db.insert_comment(video_id, session["userid"], comment, "NOW()")

    return redirect("/video/" + str(video_id))

@app.route("/create")
def create():
    return render_template("create.html")

@app.route("/create", methods=["POST"])
def create_populated():
    # todo: check if source is valid

    visual = request.form["visual"]
    audio = request.form["audio"]
    title = request.form["title"]
    desc = request.form["desc"]
    button = request.form["button"]

    visual_address = helpers.trim_link(visual)
    audio_address = helpers.trim_link(audio)
    identical = db.check_and_select_by_source(audio_address, visual_address)

    message = ""
    accept_input = True

    if identical != "-1":
        accept_input = False
        message += "Identical video already exists at [site]/video/"+identical+"\n"

    if visual_address == audio_address and visual_address != "":
        accept_input = False
        message += "Visual and audio must be from different sources >:(\n"

    if len(title) < 3 or len(title) > 100:
        accept_input = False
        message += "Title length must be 3 - 100 characters >:(\n"

    if len(desc) > 1000:
        accept_input = False
        message += "Description length must be under 1000 characters >:(\n"

    if button == "edit":
        accept_input = False

    if accept_input and button == "create":
        id = str(db.insert_video(audio_address, visual_address, title, desc, 0, "NOW()", session["userid"]))
        if not db.video_exists(id):
            accept_input = False
            message += "Video creation failed for some reason... OOPS xD... Try again"
        else:
            return redirect("/video/"+id)

    return render_template("create.html",
                            confirmed=accept_input,
                            message=message,
                            visual=visual,
                            visual_address=visual_address,
                            audio=audio,
                            audio_address=audio_address,
                            title=title,
                            desc=desc)