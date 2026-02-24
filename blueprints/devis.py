from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, make_response, current_app)
from flask_login import login_required, current_user
from models import (db, Devis, LigneDevis, Reparation,
                    Vehicule, Client, Employe, Piece, GarageConfig)
from datetime import datetime, date, timedelta
from weasyprint import HTML
import os, base64

devis_bp = Blueprint('devis_bp', __name__)

TVA_OPTIONS = [
    (18, "18% — TVA Standard (OBR Burundi)"),
    (10, "10% — TVA Réduite"),
    (0,  "0%  — Exonéré de TVA"),
]

def gen_numero_devis():
    year = datetime.now().year
    seq  = Devis.query.count() + 1
    return f"DEV-{year}-{seq:04d}"

def gen_numero_or():
    year = datetime.now().year
    seq  = Reparation.query.count() + 1
    return f"OR-{year}-{seq:04d}"


@devis_bp.route('/')
@login_required
def index():
    liste = Devis.query.order_by(Devis.created_at.desc()).all()
    return render_template('devis/index.html', devis_list=liste)


@devis_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_devis():
    clients  = Client.query.filter_by(actif=True).order_by(Client.nom).all()
    employes = Employe.query.filter_by(actif=True).order_by(Employe.nom).all()
    pieces   = Piece.query.filter_by(actif=True).order_by(Piece.nom).all()

    if request.method == 'POST':
        immat = request.form.get('immatriculation', '').strip().upper()
        if not immat:
            flash('Immatriculation obligatoire.', 'danger')
            return render_template('devis/new.html', clients=clients,
                                   employes=employes, pieces=pieces,
                                   tva_options=TVA_OPTIONS)

        veh = Vehicule.query.filter_by(immatriculation=immat).first()
        if not veh:
            client_id = request.form.get('client_id')
            if not client_id:
                flash('Selectionnez un client pour ce vehicule.', 'danger')
                return render_template('devis/new.html', clients=clients,
                                       employes=employes, pieces=pieces,
                                       tva_options=TVA_OPTIONS)
            veh = Vehicule(
                client_id=int(client_id),
                immatriculation=immat,
                marque=request.form.get('marque', '').strip(),
                modele=request.form.get('modele', '').strip(),
                annee=request.form.get('annee') or None,
            )
            db.session.add(veh)
            db.session.flush()

        tva = float(request.form.get('taux_tva', 18) or 18)
        d = Devis(
            vehicule_id=veh.id,
            numero_devis=gen_numero_devis(),
            description_panne=request.form.get('travaux', '').strip(),
            montant_mo=float(request.form.get('montant_mo', 0) or 0),
            taux_tva=tva,
            date_validite=date.today() + timedelta(days=30),
            notes=request.form.get('notes', '').strip(),
            statut='brouillon'
        )
        db.session.add(d)
        db.session.flush()

        designations = request.form.getlist('designation[]')
        quantites    = request.form.getlist('quantite[]')
        prix_list    = request.form.getlist('prix_unitaire[]')
        piece_ids    = request.form.getlist('piece_id[]')
        types_ligne  = request.form.getlist('type_ligne[]')

        for i, des in enumerate(designations):
            if des.strip():
                ligne = LigneDevis(
                    devis_id=d.id,
                    designation=des.strip(),
                    quantite=float(quantites[i] or 1),
                    prix_unitaire=float(prix_list[i] or 0),
                    piece_id=int(piece_ids[i]) if piece_ids[i] else None,
                    type_ligne=types_ligne[i] if i < len(types_ligne) else 'piece'
                )
                db.session.add(ligne)

        db.session.flush()
        d.calculer_totaux()
        db.session.commit()
        flash(f'Devis {d.numero_devis} cree avec succes.', 'success')
        return redirect(url_for('devis_bp.detail', did=d.id))

    return render_template('devis/new.html', clients=clients,
                           employes=employes, pieces=pieces,
                           tva_options=TVA_OPTIONS)


@devis_bp.route('/<int:did>')
@login_required
def detail(did):
    d      = Devis.query.get_or_404(did)
    pieces = Piece.query.filter_by(actif=True).order_by(Piece.nom).all()
    return render_template('devis/detail.html', devis=d,
                           tva_options=TVA_OPTIONS, pieces=pieces)


@devis_bp.route('/<int:did>/ajouter_ligne', methods=['POST'])
@login_required
def ajouter_ligne(did):
    d           = Devis.query.get_or_404(did)
    designation = request.form.get('designation', '').strip()
    piece_id    = request.form.get('piece_id', '').strip()
    quantite    = float(request.form.get('quantite', 1) or 1)
    prix        = float(request.form.get('prix_unitaire', 0) or 0)
    type_ligne  = request.form.get('type_ligne', 'piece')

    if piece_id:
        p = Piece.query.get(int(piece_id))
        if p:
            if not designation:
                designation = p.nom
            if prix == 0:
                prix = float(p.prix_vente)

    if not designation:
        flash('Designation obligatoire.', 'danger')
        return redirect(url_for('devis_bp.detail', did=did))

    ligne = LigneDevis(
        devis_id=did,
        piece_id=int(piece_id) if piece_id else None,
        designation=designation,
        quantite=quantite,
        prix_unitaire=prix,
        type_ligne=type_ligne
    )
    db.session.add(ligne)
    db.session.flush()
    d.calculer_totaux()
    db.session.commit()
    flash('Ligne ajoutee.', 'success')
    return redirect(url_for('devis_bp.detail', did=did))


@devis_bp.route('/ligne/<int:lid>/supprimer', methods=['POST'])
@login_required
def supprimer_ligne(lid):
    ligne = LigneDevis.query.get_or_404(lid)
    did   = ligne.devis_id
    d     = Devis.query.get(did)
    db.session.delete(ligne)
    db.session.flush()
    d.calculer_totaux()
    db.session.commit()
    flash('Ligne supprimee.', 'success')
    return redirect(url_for('devis_bp.detail', did=did))


@devis_bp.route('/<int:did>/pdf')
@login_required
def telecharger_pdf(did):
    d   = Devis.query.get_or_404(did)
    cfg = GarageConfig.query.first()

    logo_base64 = None
    if cfg and cfg.logo_filename:
        logo_path = os.path.join(current_app.config['LOGO_FOLDER'], cfg.logo_filename)
        if os.path.exists(logo_path):
            ext  = cfg.logo_filename.rsplit('.', 1)[-1].lower()
            mime = 'image/png' if ext == 'png' else 'image/jpeg'
            with open(logo_path, 'rb') as f:
                logo_base64 = f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"

    lignes_pdf = []
    for l in d.lignes:
        lignes_pdf.append({
            'designation':   l.designation,
            'type_ligne':    l.type_ligne or 'piece',
            'quantite':      float(l.quantite),
            'prix_unitaire': float(l.prix_unitaire),
            'sous_total':    float(l.quantite) * float(l.prix_unitaire),
        })

    context = dict(
        devis=d,
        cfg=cfg,
        logo_base64=logo_base64,
        lignes_pdf=lignes_pdf,
        montant_mo=float(d.montant_mo),
        montant_ht=float(d.montant_ht),
        montant_tva=float(d.montant_tva),
        montant_ttc=float(d.montant_ttc),
        taux_tva=float(d.taux_tva),
    )

    html_str = render_template('devis/pdf.html', **context)

    try:
        pdf = HTML(string=html_str).write_pdf()
        resp = make_response(pdf)
        resp.headers['Content-Type'] = 'application/pdf'
        resp.headers['Content-Disposition'] = \
            f'attachment; filename=devis-{d.numero_devis}.pdf'
        return resp
    except Exception as e:
        current_app.logger.error(f"PDF error: {e}")
        flash(f'Erreur generation PDF : {str(e)}', 'danger')
        return redirect(url_for('devis_bp.detail', did=did))


@devis_bp.route('/<int:did>/accepter', methods=['POST'])
@login_required
def accepter(did):
    d        = Devis.query.get_or_404(did)
    d.statut = 'accepte'
    r = Reparation(
        vehicule_id=d.vehicule_id,
        devis_id=d.id,
        numero_or=gen_numero_or(),
        description_panne=d.description_panne,
        montant_mo=d.montant_mo,
        taux_tva=d.taux_tva,
        statut='reception'
    )
    db.session.add(r)
    db.session.commit()
    flash(f'Devis accepte — OR {r.numero_or} cree automatiquement.', 'success')
    return redirect(url_for('reparations.detail', rid=r.id))


@devis_bp.route('/<int:did>/statut', methods=['POST'])
@login_required
def changer_statut(did):
    d        = Devis.query.get_or_404(did)
    d.statut = request.form.get('statut', d.statut)
    db.session.commit()
    flash('Statut mis a jour.', 'success')
    return redirect(url_for('devis_bp.detail', did=did))
