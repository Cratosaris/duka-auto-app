from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Client, Vehicule

clients = Blueprint('clients', __name__)

@clients.route('/')
@login_required
def index():
    q = request.args.get('q', '').strip()
    query = Client.query.filter_by(actif=True)
    if q:
        query = query.filter(
            db.or_(
                Client.nom.ilike(f'%{q}%'),
                Client.prenom.ilike(f'%{q}%'),
                Client.telephone.ilike(f'%{q}%'),
                Client.nom_entreprise.ilike(f'%{q}%')
            )
        )
    liste = query.order_by(Client.nom).all()
    return render_template('clients/index.html', clients=liste, q=q)

@clients.route('/new', methods=['GET', 'POST'])
@login_required
def new_client():
    if request.method == 'POST':
        c = Client(
            nom=request.form['nom'].strip(),
            prenom=request.form.get('prenom', '').strip(),
            telephone=request.form.get('telephone', '').strip(),
            telephone2=request.form.get('telephone2', '').strip(),
            email=request.form.get('email', '').strip(),
            adresse=request.form.get('adresse', '').strip(),
            quartier=request.form.get('quartier', '').strip(),
            ville=request.form.get('ville', 'Bujumbura').strip(),
            type_client=request.form.get('type_client', 'particulier'),
            nom_entreprise=request.form.get('nom_entreprise', '').strip(),
            nif_entreprise=request.form.get('nif_entreprise', '').strip(),
            notes=request.form.get('notes', '').strip(),
        )
        db.session.add(c)
        db.session.commit()
        flash(f'Client {c.nom_complet} créé.', 'success')
        return redirect(url_for('clients.detail', cid=c.id))
    return render_template('clients/form.html', client=None)

@clients.route('/<int:cid>')
@login_required
def detail(cid):
    c = Client.query.get_or_404(cid)
    return render_template('clients/detail.html', client=c)

@clients.route('/<int:cid>/edit', methods=['GET', 'POST'])
@login_required
def edit_client(cid):
    c = Client.query.get_or_404(cid)
    if request.method == 'POST':
        c.nom = request.form['nom'].strip()
        c.prenom = request.form.get('prenom', '').strip()
        c.telephone = request.form.get('telephone', '').strip()
        c.telephone2 = request.form.get('telephone2', '').strip()
        c.email = request.form.get('email', '').strip()
        c.adresse = request.form.get('adresse', '').strip()
        c.quartier = request.form.get('quartier', '').strip()
        c.ville = request.form.get('ville', 'Bujumbura').strip()
        c.type_client = request.form.get('type_client', 'particulier')
        c.nom_entreprise = request.form.get('nom_entreprise', '').strip()
        c.nif_entreprise = request.form.get('nif_entreprise', '').strip()
        c.notes = request.form.get('notes', '').strip()
        db.session.commit()
        flash('Client mis à jour.', 'success')
        return redirect(url_for('clients.detail', cid=c.id))
    return render_template('clients/form.html', client=c)
