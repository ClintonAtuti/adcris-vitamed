from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# Upload folder config
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE = 'database.db'


# ---------------- DATABASE ---------------- #

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    image TEXT
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    message TEXT NOT NULL
                )''')

    conn.commit()
    conn.close()


# ---------------- PUBLIC ROUTES ---------------- #

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/products')
def products():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template('products.html', products=products)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO quotes (name, email, message) VALUES (?, ?, ?)",
            (name, email, message)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('home'))

    return render_template('contact.html')


@app.route('/leadership')
def leadership():
    return render_template('leadership.html')


# ---------------- ADMIN ROUTES ---------------- #

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Move this to environment variables later
        if username == "admin" and password == "admin123":
            session['admin'] = True
            return redirect(url_for('dashboard'))

    return render_template('admin_login.html')


@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    search = request.args.get('search', '')
    category = request.args.get('category', '')
    page = int(request.args.get('page', 1))
    per_page = 5
    offset = (page - 1) * per_page

    conn = get_db_connection()

    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")

    if category:
        query += " AND category = ?"
        params.append(category)

    # Count total products
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    total = conn.execute(count_query, params).fetchone()[0]

    # Pagination
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    products = conn.execute(query, params).fetchall()

    # Get distinct categories
    categories = conn.execute("SELECT DISTINCT category FROM products").fetchall()

    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'admin_dashboard.html',
        products=products,
        search=search,
        category=category,
        categories=categories,
        total=total,
        page=page,
        total_pages=total_pages
    )


@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        description = request.form['description']
        image = request.files.get('image')

        filename = None
        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO products (name, category, description, image) VALUES (?, ?, ?, ?)",
            (name, category, description, filename)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    return render_template('add_product.html')


@app.route('/edit-product/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        description = request.form['description']

        conn.execute(
            "UPDATE products SET name=?, category=?, description=? WHERE id=?",
            (name, category, description, id)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    product = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template('edit_product.html', product=product)


@app.route('/delete-product/<int:id>')
def delete_product(id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))


# ---------------- START APP ---------------- #

init_db()

if __name__ == '__main__':
    app.run()

