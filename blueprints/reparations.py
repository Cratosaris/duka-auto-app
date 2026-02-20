from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import (db, Reparation, LignePieceReparation, Facture,
                    Vehicule, Client, Employe, Piece, Commission,
                    MouvementStock, EcritureComptable)
from datetime import datetime, date

rep_bp = Blueprint('reparations', __name__)

def gen_numero_or():
    year = datetime.now().year
    seq = Reparation.query.count() + 1
    return f"OR-{year}-{seq:04d}"

def gen_numero_facture():
    year = datetime.now().year
    seq = Facture.query.count() + 1
    return f"FAC-{year}-{seq:04d}"

@rep_bp.route('/')
@login_required
def index():
    reparations = Reparation.query.order_by(Reparation.created_at.desc()).all()
    return render_template('reparations/index.html', reparations=reparations)

@rep_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_reparation():
    clients  = Client.query.filter_by(actif=True).order_by(Client.nom).all()
    employes = Employe.query.filter_by(actif=True).order_by(Employe.nom).all()
    if request.method == 'POST':
        immat = request.form.get('immatriculation','').strip().upper()
        if not immat:
            flash('Immatriculation obligatoire.', 'danger')
            return render_template('reparations/new.html', clients=clients, employes=employes)

        veh = Vehicule.query.filter_by(immatriculation=immat).first()
        if not veh:
            client_id = request.form.get('client_id')
            if not client_id:
                flash('Sélectionnez un client pour ce nouveau véhicule.', 'danger')
                return render_template('reparations/new.html', clients=clients, employes=employes)
            veh = Vehicule(
                client_id=int(client_id),
                immatriculation=immat,
                marque=request.form.get('marque','').strip(),
                modele=request.form.get('modele','').strip(),
                annee=request.form.get('annee') or None,
                couleur=request.form.get('couleur','').strip(),
            )
            db.session.add(veh)
            db.session.flush()

        taux_tva = float(request.form.get('taux_tva', 18) or 18)
        r = Reparation(
            vehicule_id=veh.id,
            technicien_id=request.form.get('technicien_id') or None,
            numero_or=gen_numero_or(),
            description_panne=request.form.get('description_panne','').strip(),
            kilometrage_entree=request.form.get('kilometrage_entree') or None,
            taux_tva=taux_tva,
            statut='reception',
        )
        db.session.add(r)
        db.session.commit()
        flash(f'Réception créée : {r.numero_or}', 'success')
        return redirect(url_for('reparations.detail', rid=r.id))
    return render_template('reparations/new.html', clients=clients, employes=employes)

@rep_bp.route('/<int:rid>')
@login_required
def detail(rid):
    r = Reparation.query.get_or_404(rid)
    pieces_dispo = Piece.query.filter_by(actif=True).order_by(Piece.nom).all()
    return render_template('reparations/detail.html', rep=r, pieces_dispo=pieces_dispo)

@rep_bp.route('/<int:rid>/statut', methods=['POST'])
@login_required
def changer_statut(rid):
    r = Reparation.query.get_or_404(rid)
    nouveau = request.form.get('statut')
    valides = ['reception','diagnostic','devis','en_cours','termine','annule']
    if nouveau in valides:
        r.statut = nouveau
        if nouveau == 'diagnostic':
            r.date_diagnostic = datetime.now()
            r.diagnostic = request.form.get('diagnostic','').strip()
        elif nouveau == 'en_cours':
            r.date_debut_trav = datetime.now()
            r.montant_mo = float(request.form.get('montant_mo', 0) or 0)
            r.taux_tva = float(request.form.get('taux_tva', r.taux_tva) or 18)
        elif nouveau == 'termine':
            r.date_fin_trav = datetime.now()
            r.calculer_totaux()
        db.session.commit()
        flash(f'Statut mis à jour : {nouveau}', 'success')
    return redirect(url_for('reparations.detail', rid=rid))

@rep_bp.route('/<int:rid>/ajouter_piece', methods=['POST'])
@login_required
def ajouter_piece(rid):
    r = Reparation.query.get_or_404(rid)
    piece_id  = request.form.get('piece_id','').strip()
    designation = request.form.get('designation','').strip()
    quantite  = float(request.form.get('quantite', 1) or 1)
    prix      = float(request.form.get('prix_unitaire', 0) or 0)

    if piece_id:
        p = Piece.query.get(int(piece_id))
        if p:
            if not designation:
                designation = p.nom
            if prix == 0:
                prix = float(p.prix_vente)
            if p.quantite_stock >= quantite:
                p.quantite_stock -= int(quantite)
                mvt = MouvementStock(
                    piece_id=p.id, type_mvt='sortie',
                    quantite=int(quantite),
                    prix_unitaire=p.prix_vente,
                    reference_doc=r.numero_or,
                    utilisateur_id=current_user.id
                )
                db.session.add(mvt)
            else:
                flash(f'Stock insuffisant pour {p.nom} (dispo: {p.quantite_stock}).', 'warning')
                return redirect(url_for('reparations.detail', rid=rid))

    if not designation:
        flash('Désignation obligatoire.', 'danger')
        return redirect(url_for('reparations.detail', rid=rid))

    ligne = LignePieceReparation(
        reparation_id=rid,
        piece_id=int(piece_id) if piece_id else None,
        designation=designation,
        quantite=quantite,
        prix_unitaire=prix
    )
    db.session.add(ligne)
    db.session.flush()
    r.calculer_totaux()
    db.session.commit()
    flash('Pièce ajoutée.', 'success')
    return redirect(url_for('reparations.detail', rid=rid))

@rep_bp.route('/ligne/<int:lid>/supprimer', methods=['POST'])
@login_required
def supprimer_ligne(lid):
    ligne = LignePieceReparation.query.get_or_404(lid)
    rid = ligne.reparation_id
    r = Reparation.query.get(rid)
    if ligne.piece_id:
        p = Piece.query.get(ligne.piece_id)
        if p:
            p.quantite_stock += int(ligne.quantite)
    db.session.delete(ligne)
    db.session.flush()
    r.calculer_totaux()
    db.session.commit()
    flash('Ligne supprimée.', 'success')
    return redirect(url_for('reparations.detail', rid=rid))

@rep_bp.route('/<int:rid>/facturer', methods=['POST'])
@login_required
def facturer(rid):
    r = Reparation.query.get_or_404(rid)
    if r.facture:
        flash('Déjà facturé.', 'warning')
        return redirect(url_for('reparations.detail', rid=rid))
    r.calculer_totaux()
    f = Facture(
        reparation_id=rid,
        numero_facture=gen_numero_facture(),
        montant_ht=r.montant_ht,
        taux_tva=r.taux_tva,
        montant_tva=r.montant_tva,
        montant_ttc=r.montant_total,
        statut_paiement='impayee',
    )
    db.session.add(f)
    r.statut = 'facture'
    if r.technicien and float(r.technicien.taux_commission) > 0:
        montant_comm = float(r.montant_total) * float(r.technicien.taux_commission) / 100
        comm = Commission(
            employe_id=r.technicien_id,
            reparation_id=rid,
            montant=montant_comm,
            taux_applique=r.technicien.taux_commission
        )
        db.session.add(comm)
    db.session.commit()
    flash(f'Facture {f.numero_facture} créée.', 'success')
    return redirect(url_for('reparations.detail', rid=rid))

@rep_bp.route('/facture/<int:fid>/payer', methods=['POST'])
@login_required
def payer_facture(fid):
    f = Facture.query.get_or_404(fid)
    f.statut_paiement = 'payee'
    f.mode_paiement = request.form.get('mode_paiement','especes')
    f.date_paiement = datetime.now()
    ecriture = EcritureComptable(
        date_ecriture=date.today(),
        type_ecriture='recette',
        categorie='reparation',
        description=f'Paiement facture {f.numero_facture}',
        montant=f.montant_ttc,
        reference=f.numero_facture,
        utilisateur_id=current_user.id
    )
    db.session.add(ecriture)
    db.session.commit()
    flash(f'Paiement enregistré — {f.numero_facture}', 'success')
    return redirect(url_for('reparations.detail', rid=f.reparation_id))
