from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Piece, Fournisseur, MouvementStock

stock_bp = Blueprint('stock', __name__)

# ─── PIÈCES ───

@stock_bp.route('/')
@login_required
def index():
    pieces = Piece.query.filter_by(actif=True).order_by(Piece.nom).all()
    critiques = [p for p in pieces if p.stock_critique]
    return render_template('stock/index.html', pieces=pieces, critiques=critiques)

@stock_bp.route('/piece/new', methods=['GET', 'POST'])
@login_required
def new_piece():
    fournisseurs = Fournisseur.query.filter_by(actif=True).order_by(Fournisseur.nom).all()
    if request.method == 'POST':
        ref = request.form.get('reference','').strip()
        if Piece.query.filter_by(reference=ref).first():
            flash(f'Référence {ref} déjà existante.', 'danger')
            return render_template('stock/form_piece.html', piece=None, fournisseurs=fournisseurs)
        p = Piece(
            reference=ref,
            nom=request.form['nom'].strip(),
            description=request.form.get('description','').strip(),
            categorie=request.form.get('categorie','').strip(),
            prix_achat=float(request.form.get('prix_achat',0) or 0),
            prix_vente=float(request.form.get('prix_vente',0) or 0),
            quantite_stock=int(request.form.get('quantite_stock',0) or 0),
            seuil_critique=int(request.form.get('seuil_critique',5) or 5),
            unite=request.form.get('unite','pièce'),
            fournisseur_id=request.form.get('fournisseur_id') or None,
        )
        db.session.add(p)
        db.session.flush()
        if p.quantite_stock > 0:
            mvt = MouvementStock(
                piece_id=p.id, type_mvt='entree',
                quantite=p.quantite_stock,
                prix_unitaire=p.prix_achat,
                note='Stock initial',
                utilisateur_id=current_user.id
            )
            db.session.add(mvt)
        db.session.commit()
        flash(f'Pièce "{p.nom}" ajoutée avec succès.', 'success')
        return redirect(url_for('stock.index'))
    return render_template('stock/form_piece.html', piece=None, fournisseurs=fournisseurs)

@stock_bp.route('/piece/<int:pid>/edit', methods=['GET', 'POST'])
@login_required
def edit_piece(pid):
    p = Piece.query.get_or_404(pid)
    fournisseurs = Fournisseur.query.filter_by(actif=True).order_by(Fournisseur.nom).all()
    if request.method == 'POST':
        p.nom = request.form['nom'].strip()
        p.description = request.form.get('description','').strip()
        p.categorie = request.form.get('categorie','').strip()
        p.prix_achat = float(request.form.get('prix_achat',0) or 0)
        p.prix_vente = float(request.form.get('prix_vente',0) or 0)
        p.seuil_critique = int(request.form.get('seuil_critique',5) or 5)
        p.unite = request.form.get('unite','pièce')
        p.fournisseur_id = request.form.get('fournisseur_id') or None
        db.session.commit()
        flash('Pièce mise à jour.', 'success')
        return redirect(url_for('stock.index'))
    return render_template('stock/form_piece.html', piece=p, fournisseurs=fournisseurs)

@stock_bp.route('/piece/<int:pid>/ajuster', methods=['POST'])
@login_required
def ajuster_stock(pid):
    p = Piece.query.get_or_404(pid)
    qte = int(request.form.get('quantite', 0))
    type_mvt = request.form.get('type_mvt', 'entree')
    note = request.form.get('note', '').strip()
    if type_mvt == 'sortie':
        if p.quantite_stock < qte:
            flash('Stock insuffisant.', 'danger')
            return redirect(url_for('stock.index'))
        p.quantite_stock -= qte
    else:
        p.quantite_stock += qte
    mvt = MouvementStock(
        piece_id=p.id, type_mvt=type_mvt,
        quantite=qte, note=note,
        utilisateur_id=current_user.id
    )
    db.session.add(mvt)
    db.session.commit()
    flash(f'Stock ajusté : {p.nom} → {p.quantite_stock} {p.unite}', 'success')
    return redirect(url_for('stock.index'))

# ─── FOURNISSEURS ───

@stock_bp.route('/fournisseurs')
@login_required
def fournisseurs():
    liste = Fournisseur.query.order_by(Fournisseur.nom).all()
    return render_template('stock/fournisseurs.html', fournisseurs=liste)

@stock_bp.route('/fournisseur/new', methods=['GET', 'POST'])
@login_required
def new_fournisseur():
    if request.method == 'POST':
        f = Fournisseur(
            nom=request.form['nom'].strip(),
            contact=request.form.get('contact','').strip(),
            telephone=request.form.get('telephone','').strip(),
            email=request.form.get('email','').strip(),
            adresse=request.form.get('adresse','').strip(),
            type_fourn=request.form.get('type_fourn','local'),
            pays_origine=request.form.get('pays_origine','').strip(),
            nif=request.form.get('nif','').strip(),
        )
        db.session.add(f)
        db.session.commit()
        flash(f'Fournisseur "{f.nom}" ajouté.', 'success')
        return redirect(url_for('stock.fournisseurs'))
    return render_template('stock/form_fournisseur.html', fournisseur=None)

@stock_bp.route('/fournisseur/<int:fid>/edit', methods=['GET', 'POST'])
@login_required
def edit_fournisseur(fid):
    f = Fournisseur.query.get_or_404(fid)
    if request.method == 'POST':
        f.nom = request.form['nom'].strip()
        f.contact = request.form.get('contact','').strip()
        f.telephone = request.form.get('telephone','').strip()
        f.email = request.form.get('email','').strip()
        f.adresse = request.form.get('adresse','').strip()
        f.type_fourn = request.form.get('type_fourn','local')
        f.pays_origine = request.form.get('pays_origine','').strip()
        f.nif = request.form.get('nif','').strip()
        f.actif = request.form.get('actif') == 'on'
        db.session.commit()
        flash('Fournisseur mis à jour.', 'success')
        return redirect(url_for('stock.fournisseurs'))
    return render_template('stock/form_fournisseur.html', fournisseur=f)
