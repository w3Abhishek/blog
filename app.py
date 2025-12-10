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
    page = request.args.get('page', 1, type=int)
    per_page = 5
    start = (page - 1) * per_page
    end = start + per_page - 1

    try:
        # Fetch posts with pagination
        response = supabase.table('posts').select("*", count='exact').eq('published', True).order('created_at', desc=True).range(start, end).execute()
        posts = response.data
        total_count = response.count
        
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
    except Exception as e:
        print(f"Error fetching posts: {e}")
        posts = []
        total_pages = 0
        has_next = False
        has_prev = False

    return render_template('index.html', posts=posts, page=page, total_pages=total_pages, has_next=has_next, has_prev=has_prev)

@app.route('/post/<slug>')
def post_detail(slug):
    try:
        # Fetch current post
        response = supabase.table('posts').select("*").eq('slug', slug).eq('published', True).execute()
        if not response.data:
            abort(404)
        post = response.data[0]
        
        # Fetch previous post (older)
        prev_response = supabase.table('posts').select("title, slug").eq('published', True).lt('created_at', post['created_at']).order('created_at', desc=True).limit(1).execute()
        prev_post = prev_response.data[0] if prev_response.data else None
        
        # Fetch next post (newer)
        next_response = supabase.table('posts').select("title, slug").eq('published', True).gt('created_at', post['created_at']).order('created_at', desc=False).limit(1).execute()
        next_post = next_response.data[0] if next_response.data else None
        
    except Exception as e:
        print(f"Error fetching post: {e}")
        abort(404)
    return render_template('post.html', post=post, prev_post=prev_post, next_post=next_post)

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
