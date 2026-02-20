from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from models import db, Devis, LigneDevis, Reparation, Vehicule, Client, Employe, Piece, GarageConfig
from datetime import datetime, date, timedelta
from weasyprint import HTML
import flask

devis_bp = Blueprint('devis_bp', __name__)

def gen_numero_devis():
    year = datetime.now().year
    seq = Devis.query.count() + 1
    return f"DEV-{year}-{seq:04d}"

def gen_numero_or():
    year = datetime.now().year
    seq = Reparation.query.count() + 1
    return f"OR-{year}-{seq:04d}"

TVA_OPTIONS = [
    (18, "18% — TVA Standard (OBR)"),
    (10, "10% — TVA Réduite (services spéciaux)"),
    (0,  "0% — Exonéré de TVA"),
]

@devis_bp.route('/')
@login_required
def index():
    liste = Devis.query.order_by(Devis.created_at.desc()).all()
    return render_template('devis/index.html', devis_list=liste)

@devis_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_devis():
    clients = Client.query.filter_by(actif=True).order_by(Client.nom).all()
    employes = Employe.query.filter_by(actif=True).order_by(Employe.nom).all()
    pieces = Piece.query.filter_by(actif=True).order_by(Piece.nom).all()
    if request.method == 'POST':
        veh = Vehicule.query.filter_by(
            immatriculation=request.form['immatriculation'].strip().upper()
        ).first()
        if not veh:
            client_id = request.form.get('client_id')
            if not client_id:
                flash('Sélectionnez un client.', 'danger')
                return render_template('devis/new.html', clients=clients, employes=employes, pieces=pieces, tva_options=TVA_OPTIONS)
            veh = Vehicule(
                client_id=int(client_id),
                immatriculation=request.form['immatriculation'].strip().upper(),
                marque=request.form.get('marque','').strip(),
                modele=request.form.get('modele','').strip(),
                annee=request.form.get('annee') or None,
            )
            db.session.add(veh)
            db.session.flush()

        tva = float(request.form.get('taux_tva', 18))
        d = Devis(
            vehicule_id=veh.id,
            technicien_id=request.form.get('technicien_id') or None,
            numero_devis=gen_numero_devis(),
            description_panne=request.form.get('description_panne','').strip(),
            montant_mo=float(request.form.get('montant_mo', 0) or 0),
            taux_tva=tva,
            date_validite=date.today() + timedelta(days=30),
            notes=request.form.get('notes','').strip(),
            statut='brouillon'
        )
        db.session.add(d)
        db.session.flush()

        # Lignes
        designations = request.form.getlist('designation[]')
        quantites = request.form.getlist('quantite[]')
        prix = request.form.getlist('prix_unitaire[]')
        piece_ids = request.form.getlist('piece_id[]')
        for i, des in enumerate(designations):
            if des.strip():
                ligne = LigneDevis(
                    devis_id=d.id,
                    designation=des.strip(),
                    quantite=float(quantites[i] or 1),
                    prix_unitaire=float(prix[i] or 0),
                    piece_id=int(piece_ids[i]) if piece_ids[i] else None
                )
                db.session.add(ligne)

        db.session.flush()
        d.calculer_totaux()
        db.session.commit()
        flash(f'Devis {d.numero_devis} créé.', 'success')
        return redirect(url_for('devis_bp.detail', did=d.id))
    return render_template('devis/new.html', clients=clients, employes=employes, pieces=pieces, tva_options=TVA_OPTIONS)

@devis_bp.route('/<int:did>')
@login_required
def detail(did):
    d = Devis.query.get_or_404(did)
    return render_template('devis/detail.html', devis=d, tva_options=TVA_OPTIONS)

@devis_bp.route('/<int:did>/pdf')
@login_required
def telecharger_pdf(did):
    d = Devis.query.get_or_404(did)
    cfg = GarageConfig.query.first()
    html_str = flask.render_template('devis/pdf.html', devis=d, cfg=cfg)
    pdf = HTML(string=html_str, base_url=flask.request.host_url).write_pdf()
    resp = make_response(pdf)
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = f'attachment; filename=devis-{d.numero_devis}.pdf'
    return resp

@devis_bp.route('/<int:did>/accepter', methods=['POST'])
@login_required
def accepter(did):
    d = Devis.query.get_or_404(did)
    d.statut = 'accepte'
    # Créer OR automatiquement
    r = Reparation(
        vehicule_id=d.vehicule_id,
        technicien_id=d.technicien_id,
        devis_id=d.id,
        numero_or=gen_numero_or(),
        description_panne=d.description_panne,
        montant_mo=d.montant_mo,
        taux_tva=d.taux_tva,
        statut='reception'
    )
    db.session.add(r)
    db.session.commit()
    flash(f'Devis accepté — Ordre de réparation {r.numero_or} créé.', 'success')
    return redirect(url_for('reparations.detail', rid=r.id))

@devis_bp.route('/<int:did>/statut', methods=['POST'])
@login_required
def changer_statut(did):
    d = Devis.query.get_or_404(did)
    d.statut = request.form.get('statut', d.statut)
    db.session.commit()
    flash('Statut mis à jour.', 'success')
    return redirect(url_for('devis_bp.detail', did=did))
