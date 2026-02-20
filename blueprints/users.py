from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Utilisateur
from functools import wraps

users = Blueprint('users', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Accès réservé aux administrateurs.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

@users.route('/')
@login_required
@admin_required
def index():
    liste = Utilisateur.query.order_by(Utilisateur.username).all()
    return render_template('users/index.html', users=liste)

@users.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    if request.method == 'POST':
        if Utilisateur.query.filter_by(username=request.form['username'].strip()).first():
            flash('Ce nom d\'utilisateur existe déjà.', 'danger')
            return render_template('users/form.html', user=None)
        u = Utilisateur(
            username=request.form['username'].strip(),
            email=request.form['email'].strip(),
            nom_complet=request.form.get('nom_complet', '').strip(),
            telephone=request.form.get('telephone', '').strip(),
            role=request.form.get('role', 'technicien'),
            actif=True
        )
        u.set_password(request.form['password'])
        db.session.add(u)
        db.session.commit()
        flash(f'Utilisateur {u.username} créé.', 'success')
        return redirect(url_for('users.index'))
    return render_template('users/form.html', user=None)

@users.route('/<int:uid>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(uid):
    u = Utilisateur.query.get_or_404(uid)
    if request.method == 'POST':
        u.email = request.form['email'].strip()
        u.nom_complet = request.form.get('nom_complet', '').strip()
        u.telephone = request.form.get('telephone', '').strip()
        u.role = request.form.get('role', u.role)
        u.actif = request.form.get('actif') == 'on'
        if request.form.get('password'):
            u.set_password(request.form['password'])
        db.session.commit()
        flash('Utilisateur mis à jour.', 'success')
        return redirect(url_for('users.index'))
    return render_template('users/form.html', user=u)
