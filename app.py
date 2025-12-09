from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.route('/')
def index():
    try:
        response = supabase.table('posts').select("*").eq('published', True).order('created_at', desc=True).execute()
        posts = response.data
    except Exception as e:
        print(f"Error fetching posts: {e}")
        posts = []
    return render_template('index.html', posts=posts)

@app.route('/post/<slug>')
def post_detail(slug):
    try:
        response = supabase.table('posts').select("*").eq('slug', slug).eq('published', True).execute()
        if not response.data:
            abort(404)
        post = response.data[0]
    except Exception as e:
        print(f"Error fetching post: {e}")
        abort(404)
    return render_template('post.html', post=post)

# Admin Routes
def is_logged_in():
    return session.get('logged_in')

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if is_logged_in():
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password')
    
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('admin_login'))
    
    try:
        response = supabase.table('posts').select("*").order('created_at', desc=True).execute()
        posts = response.data
    except Exception as e:
        print(f"Error fetching posts: {e}")
        posts = []
    return render_template('admin/dashboard.html', posts=posts)

@app.route('/admin/new', methods=['GET', 'POST'])
def new_post():
    if not is_logged_in():
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        slug = request.form.get('slug')
        content = request.form.get('content')
        category = request.form.get('category')
        tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
        published = 'published' in request.form
        
        try:
            data = {
                'title': title,
                'slug': slug,
                'content': content,
                'category': category,
                'tags': tags,
                'published': published
            }
            supabase.table('posts').insert(data).execute()
            flash('Post created successfully')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error creating post: {e}')
    
    return render_template('admin/editor.html', post=None)

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def edit_post(id):
    if not is_logged_in():
        return redirect(url_for('admin_login'))
    
    try:
        response = supabase.table('posts').select("*").eq('id', id).execute()
        if not response.data:
            abort(404)
        post = response.data[0]
    except Exception as e:
        flash(f'Error fetching post: {e}')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        slug = request.form.get('slug')
        content = request.form.get('content')
        category = request.form.get('category')
        tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
        published = 'published' in request.form
        
        try:
            data = {
                'title': title,
                'slug': slug,
                'content': content,
                'category': category,
                'tags': tags,
                'published': published
            }
            supabase.table('posts').update(data).eq('id', id).execute()
            flash('Post updated successfully')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error updating post: {e}')

    return render_template('admin/editor.html', post=post)

@app.route('/admin/delete/<int:id>', methods=['POST'])
def delete_post(id):
    if not is_logged_in():
        return redirect(url_for('admin_login'))
    
    try:
        supabase.table('posts').delete().eq('id', id).execute()
        flash('Post deleted successfully')
    except Exception as e:
        flash(f'Error deleting post: {e}')
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
