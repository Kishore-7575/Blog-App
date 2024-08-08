import os
from functools import wraps
import sqlite3
from flask import Flask, render_template, flash, redirect, url_for, session, request, jsonify
from werkzeug.utils import secure_filename
from wtforms import Form, StringField, PasswordField, validators, FileField, SelectField, TextAreaField, SubmitField
from flask_ckeditor import CKEditor, CKEditorField
from passlib.hash import sha256_crypt
from flask_wtf.file import FileField
from datetime import datetime
import re
import sqlite3
from wtforms.validators import DataRequired, Email
from flask_wtf import FlaskForm



dbConnection = sqlite3.connect("blog.db", check_same_thread=False)
dbConnection.row_factory = sqlite3.Row
dbCursor = dbConnection.cursor()

dbArticlesQuery = """CREATE TABLE IF NOT EXISTS articles(
                     articleID INTEGER PRIMARY KEY AUTOINCREMENT,
                     title TEXT,
                     author TEXT,
                     content TEXT,
                     image TEXT,
                     created_date DATETIME DEFAULT CURRENT_TIMESTAMP
                     )"""


dbUsersQuery = """CREATE TABLE IF NOT EXISTS users(
                    userID INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    username TEXT,
                    email TEXT,
                    password TEXT
                )"""

dbCursor.execute(dbArticlesQuery)
dbCursor.execute(dbUsersQuery)
dbConnection.commit()

# APP SETTINGS
app = Flask(__name__)
app.secret_key = "flask-blog-app"
ckeditor = CKEditor(app)
app.config["SESSION_TYPE"] = "filesystem"
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.static_folder = "static"

# LOGIN CHECK
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "loggedIn" in session:
            return f(*args, **kwargs)
        flash("You must log in to view this page", "warning")
        return redirect(url_for("login"))
    return decorated_function

# ADMIN CHECK
def adminCheck():
    if session.get("username") == "admin":
        return True
    return False

# REGISTER FORM
class RegisterForm(Form):
    name = StringField("Full Name", validators=[validators.input_required()])
    username = StringField(
        "Username",
        validators=[validators.input_required(), validators.Length(min=5, max=30)],
    )
    email = StringField(
        "Email", validators=[validators.Email(message="Please type a valid email")]
    )
    password = PasswordField(
        "Password",
        validators=[
            validators.input_required(),
            validators.Length(min=7),
            validators.EqualTo(fieldname="confirm", message="Password don't match"),
        ],
    )
    confirm = PasswordField("Confirm Password")

# LOGIN FORM
class LoginForm(Form):
    username = StringField("Username")
    password = PasswordField("Password")

# ARTICLE FORM
from wtforms import StringField, TextAreaField, SelectField
from wtforms.validators import DataRequired

class ArticleForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    declaration = StringField('Declaration', validators=[DataRequired()])
    category = SelectField('Category', choices=[], validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    hashtags = StringField('Hashtags')
    image = FileField('Image')


class CommentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    comment = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Post Comment')


@app.route("/comments")
def comments():
    query = """
    SELECT c.name, c.email, c.comment, c.created_date, a.title, a.category, a.image
    FROM comments c
    JOIN articles a ON c.article_id = a.articleID
    ORDER BY c.created_date DESC
    """
    dbCursor.execute(query)
    comments = dbCursor.fetchall()

    return render_template("comments.html", comments=comments)



# INDEX
@app.route("/")
def index():
    conn = get_db_connection()
    query = "SELECT * FROM articles LIMIT 5"
    articles = conn.execute(query).fetchall()
    conn.close()
    return render_template("index.html", articles=articles)


# INDEX 2
@app.route("/index")
def index2():
    return redirect(url_for("index"))

# ABOUT
@app.route("/about")
def about():
    return render_template("about.html")

# DASHBOARD
@app.route("/admin")
@login_required
def dashboard():
    if adminCheck():
        query = "SELECT * FROM articles"
        dbCursor.execute(query)
        result = dbCursor.fetchall()
    else:
        query = "SELECT * FROM articles WHERE author = ?"
        dbCursor.execute(query, (session["username"],))
        result = dbCursor.fetchall()
    if len(result) > 0:
        articles = result
        return render_template("dashboard.html", articles=articles)
    return render_template("dashboard.html")

# ARTICLES
@app.route("/articles")
def articles():
    query = "SELECt * FROM articles"
    dbCursor.execute(query)
    result = dbCursor.fetchall()
    if len(result) > 0:
        articles = result
        return render_template("articles.html", articles=articles)
    return render_template("articles.html")

# USER ARTICLES
@app.route("/userArticles/<string:author>")
def userArticles(author):
    query = "SELECT * FROM articles WHERE author = ?"
    dbCursor.execute(query, (author,))
    result = dbCursor.fetchall()
    if len(result) > 0:
        articles = result
        return render_template("userArticles.html", articles=articles, author=author)
    return render_template("userArticles.html")

# ARTICLE
def get_db_connection():
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/article/<string:articleID>", methods=["GET", "POST"])
def article(articleID):
    query = "SELECT * FROM articles WHERE articleID = ?"
    dbCursor.execute(query, (articleID,))
    article = dbCursor.fetchone()

    if not article:
        flash("There is no such article.", "warning")
        return redirect(url_for("index"))

    form = CommentForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        comment = form.comment.data

        dbCursor.execute("INSERT INTO comments (article_id, name, email, comment) VALUES (?, ?, ?, ?)", 
                         (articleID, name, email, comment))
        dbConnection.commit()
        flash("Your comment has been posted.", "success")
        return redirect(url_for("article", articleID=articleID))

    dbCursor.execute("SELECT * FROM comments WHERE article_id = ? ORDER BY created_date DESC", (articleID,))
    comments = dbCursor.fetchall()

    related_articles = get_related_articles(article["category"], articleID)

    return render_template("article.html", article=article, related_articles=related_articles, form=form, comments=comments)

def get_related_articles(category, exclude_article_id, limit=5):
    query = "SELECT * FROM articles WHERE category = ? AND articleID != ? ORDER BY created_date DESC LIMIT ?"
    dbCursor.execute(query, (category, exclude_article_id, limit))
    return dbCursor.fetchall()



def get_db_connection():
    conn = sqlite3.connect('blog.db', timeout=10)  # 10-second timeout
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/media")
@login_required
def media():
    images = set()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT image, content FROM articles"
        cursor.execute(query)
        articles = cursor.fetchall()
        
        for article in articles:
            if article['image']:
                images.add(article['image'])
            
            content_images = re.findall(r'<img[^>]+src="([^">]+)"', article['content'])
            images.update(content_images)
    
    except sqlite3.OperationalError as e:
        app.logger.error(f"Database error while fetching media: {e}")
        return "Database error while fetching media", 500
    except Exception as e:
        app.logger.error(f"Unexpected error while fetching media: {e}")
        return "Unexpected error occurred", 500
    finally:
        conn.close()
    
    return render_template("media.html", images=list(images))


def get_db_connection():
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/add_category", methods=["POST"])
def add_category():
    category_name = request.form.get("categoryName")
    description = request.form.get("description")

    if category_name:
        try:
            conn = get_db_connection()
            conn.execute("INSERT INTO categories (name, description) VALUES (?, ?)", (category_name, description))
            conn.commit()
            conn.close()
            flash("Category added successfully!", "success")
        except Exception as e:
            flash(f"Error adding category: {e}", "danger")
    else:
        flash("Category name is required.", "warning")

    return redirect(url_for("categories"))

@app.route("/categories")
def categories():
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return render_template("categories.html", categories=categories)


@app.route("/delete_category/<int:category_id>")
def delete_category(category_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()
    flash("Category deleted successfully!", "success")
    return redirect(url_for("categories"))

@app.route("/add_hashtag", methods=["POST"])
def add_hashtag():
    hashtag_name = request.form.get("hashtagName")
    description = request.form.get("description")

    if hashtag_name:
        try:
            conn = get_db_connection()
            conn.execute("INSERT INTO hashtags (name, description) VALUES (?, ?)", (hashtag_name, description))
            conn.commit()
            conn.close()
            flash("Hashtag added successfully!", "success")
        except Exception as e:
            flash(f"Error adding hashtag: {e}", "danger")
    else:
        flash("Hashtag name is required.", "warning")

    return redirect(url_for("hashtags"))

@app.route("/hashtags")
def hashtags():
    conn = get_db_connection()
    hashtags = conn.execute("SELECT * FROM hashtags ORDER BY name").fetchall()
    conn.close()
    return render_template("hashtags.html", hashtags=hashtags)


@app.route("/delete_hashtag/<int:hashtag_id>")
def delete_hashtag(hashtag_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM hashtags WHERE id = ?", (hashtag_id,))
    conn.commit()
    conn.close()
    flash("Hashtag deleted successfully!", "success")
    return redirect(url_for("hashtags"))



@app.route('/deleteImages', methods=['POST'])
@login_required
def delete_images():
    try:
        data = request.get_json()
        app.logger.info(f"Received data: {data}")
        images = data.get('images', [])

        if not images:
            return jsonify({'success': False, 'message': 'No images provided'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("BEGIN")

        for image in images:
            app.logger.info(f"Processing image: {image}")
            
            # Remove image from the content of blog posts
            cursor.execute(
                "UPDATE articles SET content = REPLACE(content, ?, '')",
                (f'<img src="{image}"',)
            )

            # Optionally: Remove the image file from the server
            image_path = os.path.join(app.root_path, 'static/uploads', os.path.basename(image))
            if os.path.exists(image_path):
                os.remove(image_path)
            else:
                app.logger.error(f"Image file not found: {image_path}")

        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except sqlite3.OperationalError as e:
        app.logger.error(f"Database error while deleting images: {e}")
        return jsonify({'success': False, 'message': 'Database is locked. Try again later.'}), 503
    except Exception as e:
        app.logger.error(f"Unexpected error while deleting images: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


UPLOAD_FOLDER = os.path.join(app.root_path, 'static/uploads')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



from flask import g, request

# @app.context_processor
# @login_required
# def inject_sidebar():
#     is_authenticated = 'user_id' in session
#     current_endpoint = request.endpoint
#     sidebar_endpoints = ['add_article', 'edit_article', 'dashboard']

#     show_sidebar = is_authenticated and current_endpoint in sidebar_endpoints

#     return dict(show_sidebar=show_sidebar)



@app.route('/updateImage', methods=['POST'])
@login_required
def update_image():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400

    file = request.files['file']
    old_image = request.form.get('oldImage')

    if not file or not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file'}), 400

    if old_image:
        # Remove old image from the server
        old_image_path = os.path.join(UPLOAD_FOLDER, os.path.basename(old_image))
        if os.path.exists(old_image_path):
            os.remove(old_image_path)

    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update image reference in the database
        cursor.execute(
            "UPDATE articles SET image = ? WHERE image = ?",
            (filename, os.path.basename(old_image))
        )
        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except sqlite3.OperationalError as e:
        app.logger.error(f"Database error while updating image: {e}")
        return jsonify({'success': False, 'message': 'Database error'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error while updating image: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/addArticle", methods=["GET", "POST"])
@login_required
def addArticle():
    form = ArticleForm(request.form)
    dbCursor.execute("SELECT name FROM categories")
    categories = dbCursor.fetchall()
    form.category.choices = [(category["name"], category["name"]) for category in categories]

    if request.method == "POST":
        title = form.title.data
        declaration = form.declaration.data
        category = form.category.data
        content = form.content.data
        hashtags = form.hashtags.data
        image_url = None

        if 'image' in request.files:
            image = request.files['image']
            if image:
                filename = secure_filename(image.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(filepath)
                image_url = url_for('static', filename='uploads/' + filename)

        query = "INSERT INTO articles(title, author, content, declaration, category, image, hashtags) VALUES(?, ?, ?, ?, ?, ?, ?)"
        dbCursor.execute(query, (title, session["username"], content, declaration, category, image_url, hashtags))
        dbConnection.commit()
        flash("Article has been added successfully", "success")
        return redirect(url_for("dashboard"))

    return render_template("addArticle.html", form=form)

@app.route("/migrate")
def migrate():
    try:
        # Add category and hashtags tables
        dbCursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
        """)
        dbCursor.execute("""
            CREATE TABLE IF NOT EXISTS hashtags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
        """)
        dbConnection.commit()
        return "Migration successful!", 200
    except Exception as e:
        print(f"An error occurred: {e}")
        return "Migration failed!", 500

@app.route("/editArticle/<string:articleID>", methods=["GET", "POST"])
@login_required
def editArticle(articleID):
    # Fetch article from the database
    dbCursor.execute("SELECT * FROM articles WHERE articleID = ?", (articleID,))
    article = dbCursor.fetchone()
    
    if not article:
        flash("There is no such article or you may not have the permission to edit", "warning")
        return redirect(url_for("dashboard"))
    
    # Initialize the form with existing data
    form = ArticleForm(request.form)
    dbCursor.execute("SELECT name FROM categories")
    categories = dbCursor.fetchall()
    form.category.choices = [(category["name"], category["name"]) for category in categories]
    
    if request.method == "POST":
        if form:
            titleUpdated = form.title.data
            declarationUpdated = form.declaration.data
            categoryUpdated = form.category.data
            contentUpdated = form.content.data
            hashtagsUpdated = form.hashtags.data
            image_url = None

            if 'image' in request.files:
                image = request.files['image']
                if image and image.filename != '':
                    filename = secure_filename(image.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image.save(filepath)
                    image_url = url_for('static', filename='uploads/' + filename)

            created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if image_url:
                query = """UPDATE articles 
                           SET title = ?, content = ?, declaration = ?, category = ?, image = ?, hashtags = ?, created_date = ? 
                           WHERE articleID = ?"""
                dbCursor.execute(query, (titleUpdated, contentUpdated, declarationUpdated, categoryUpdated, image_url, hashtagsUpdated, created_date, articleID))
            else:
                query = """UPDATE articles 
                           SET title = ?, content = ?, declaration = ?, category = ?, hashtags = ?, created_date = ? 
                           WHERE articleID = ?"""
                dbCursor.execute(query, (titleUpdated, contentUpdated, declarationUpdated, categoryUpdated, hashtagsUpdated, created_date, articleID))

            dbConnection.commit()
            flash("Article has been updated successfully", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Error updating the article. Please check your input.", "danger")
    
    # If GET or invalid POST, render the form with existing article data
    form.title.data = article["title"]
    form.declaration.data = article["declaration"]
    form.category.data = article["category"]
    form.content.data = article["content"]
    form.hashtags.data = article["hashtags"]
    
    return render_template("editArticle.html", form=form, article=article)


# DELETE ARTICLE
@app.route("/deleteArticle/<string:articleID>")
@login_required
def deleteArticle(articleID):
    if adminCheck():
        query = "SELECT * FROM articles WHERE articleID = ?"
        dbCursor.execute(query, (articleID,))
        result = dbCursor.fetchall()
    else:
        query = "SELECT * FROM articles WHERE author = ? and articleID = ?"
        dbCursor.execute(query, (session["username"], articleID))
        result = dbCursor.fetchall()
    if len(result) > 0:
        query = "DELETE FROM articles WHERE articleID = ?"
        dbCursor.execute(query, (articleID,))
        dbConnection.commit()
        flash("Article has been deleted successfully", "success")
        return redirect(url_for("dashboard"))
    flash(
        "There is no such article or you may have not the permission to delete",
        "warning",
    )
    return redirect(url_for("dashboard"))

# SEARCH ARTICLE
@app.route("/searchArticle", methods=["GET", "POST"])
def searchArticle():
    if request.method == "GET":
        return redirect(url_for("index"))
    keyword = request.form.get("keyword")
    if not keyword:
        return redirect(url_for("index"))
    query = "SELECT * FROM articles WHERE title LIKE ?"
    dbCursor.execute(query, ("%" + keyword + "%",))
    result = dbCursor.fetchall()
    if len(result) > 0:
        articles = result
        return render_template("searchArticle.html", articles=articles)
    flash("No articles found with this keyword", "warning")
    return redirect(url_for("articles"))

# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        query = "SELECT * FROM users WHERE username = ? or email = ?"
        dbCursor.execute(query, (username, email))
        result = dbCursor.fetchall()
        if len(result) > 0:
            article = result[0]
            if article[2] == username:
                flash("This username is used. Please, choose another one.", "warning")
                return redirect(url_for("register"))
            elif article[3] == email:
                flash("This email address is used. Please, choose another one.", "warning")
                return redirect(url_for("register"))
        query = "INSERT INTO users(name, username, email, password) VALUES(?, ?, ?, ?)"
        dbCursor.execute(query, (name, username, email, password))
        dbConnection.commit()
        flash("You have been registered successfully", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)

# LOGIN
@app.route("/my-login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        passwordCandidate = form.password.data
        query = "SELECT * FROM users WHERE username = ?"
        dbCursor.execute(query, (username,))
        result = dbCursor.fetchall()
        if len(result) > 0:
            data = result[0]
            realPassword = data["password"]
            if sha256_crypt.verify(passwordCandidate, realPassword):
                session["loggedIn"] = True
                session["username"] = username
                flash("You have been logged in successfully", "success")
                return redirect(url_for("index"))
            flash("Invalid password", "danger")
            return redirect(url_for("login"))
        flash("Invalid username", "danger")
        return redirect(url_for("login"))
    return render_template("login.html", form=form)

# LOGOUT
@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'upload' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['upload']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        url = url_for('static', filename='uploads/' + filename)
        return jsonify({'url': url})

    return jsonify({'error': 'File upload failed'})

# ERROR PAGE 404
@app.errorhandler(404)
def error404(e):
    return render_template("404.html")

if __name__ == "__main__":
    app.run(port=5000, debug=True)
