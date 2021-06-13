from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
#from data import Articles
from flask_mysqldb import MySQL
from functools import wraps
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from slugify import slugify

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'admin'
app.config['MYSQL_PASSWORD'] = 'pass123'
app.config['MYSQL_DB'] = 'myblogger'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init mysql
mysql = MySQL(app)

#rticles = Articles()

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/articles')
def articles():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()
    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No articles found'
        return render_template('articles.html')

    cur.close()

@app.route('/article/<string:slug>/')
def article(slug):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles WHERE slug=%s", [slug])

    article = cur.fetchone()
    return render_template('article.html', article=article)

class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Password does not match')
    ])
    confirm = PasswordField('Confirm Password')
    twitter = StringField('Twitter', [validators.Length(min=4, max=100)])
    linkedin = StringField('LinkedIn', [validators.Length(min=4, max=100)])
    instagram = StringField('Instagram', [validators.Length(min=4, max=100)])

@app.route('/register', methods = ['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.hash(str(form.password.data))
        twitter = form.twitter.data
        linkedin = form.linkedin.data
        instagram = form.instagram.data

        # create cursor
        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO users(name, email, username, password, twitter, linkedin, instagram) VALUES(%s, %s, %s, %s, %s, %s, %s)", (name, email,username, password, twitter, linkedin, instagram))

        #commit to DB
        mysql.connection.commit()
        #close connection
        cur.close()

        flash('Registered successfully', 'success')

        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password'] 

        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# check if user is logged in
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, requires login', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    curr_user = session['username']
    result = cur.execute("SELECT * FROM articles WHERE author = %s", [curr_user])

    articles = cur.fetchall()
    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No articles found'
        return render_template('dashboard.html')

    cur.close()

class ArticleForm(Form):
    title = StringField('Title', [validators.length(min=1, max=200)])
    body = TextAreaField('Body', [validators.length(min=30)])
@app.route('/add_article', methods=['GET', 'POST'])
@login_required
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data
        slug = slugify(title)

        cur_user = mysql.connection.cursor()
        cur_user.execute("SELECT * FROM users WHERE username=%s",[session['username']])
        user = cur_user.fetchone()
    
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO articles(title, body, author, slug, twitter, linkedin, instagram) VALUES(%s, %s, %s, %s, %s, %s, %s)",(title, body, session['username'],slug,user['twitter'],user['linkedin'], user['instagram']))

        mysql.connection.commit()
        cur_user.close()
        cur.close()
        flash('Article created', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_article.html',form=form)


@app.route('/edit_article/<string:slug>', methods=['GET', 'POST'])
@login_required
def edit_article(slug):

    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles WHERE slug = %s",[slug])
    article = cur.fetchone()

    form = ArticleForm(request.form)
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']
        newSlug = slugify(title)

        cur = mysql.connection.cursor()
        cur.execute("UPDATE articles SET title = %s, body = %s, slug = %s WHERE slug = %s", (title ,body, newSlug,slug))

        mysql.connection.commit()
        cur.close()

        flash('Article updated', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_article.html',form=form)

@app.route('/delete_article/<string:slug>', methods=['POST'])
@login_required
def delete_article(slug):

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM articles WHERE slug = %s",[slug])
    mysql.connection.commit()
    cur.close()

    flash('Article deleted', 'success')
    return redirect(url_for('dashboard'))

    
if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)