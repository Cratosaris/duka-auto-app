from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Employe, Presence
from datetime import datetime, date

rh_bp = Blueprint('rh', __name__)

@rh_bp.route('/')
@login_required
def index():
    employes = Employe.query.filter_by(actif=True).order_by(Employe.nom).all()
    return render_template('rh/index.html', employes=employes)

@rh_bp.route('/employe/new', methods=['GET', 'POST'])
@login_required
def new_employe():
    if request.method == 'POST':
        e = Employe(
            nom=request.form['nom'].strip(),
            prenom=request.form['prenom'].strip(),
            poste=request.form.get('poste', '').strip(),
            telephone=request.form.get('telephone', '').strip(),
            email=request.form.get('email', '').strip(),
            salaire_base=request.form.get('salaire_base', 0) or 0,
            taux_commission=request.form.get('taux_commission', 0) or 0,
        )
        db.session.add(e)
        db.session.commit()
        flash(f'Employé {e.nom_complet} ajouté.', 'success')
        return redirect(url_for('rh.index'))
    return render_template('rh/form_employe.html', employe=None)

@rh_bp.route('/employe/<int:eid>/edit', methods=['GET', 'POST'])
@login_required
def edit_employe(eid):
    e = Employe.query.get_or_404(eid)
    if request.method == 'POST':
        e.nom = request.form['nom'].strip()
        e.prenom = request.form['prenom'].strip()
        e.poste = request.form.get('poste', '').strip()
        e.telephone = request.form.get('telephone', '').strip()
        e.email = request.form.get('email', '').strip()
        e.salaire_base = request.form.get('salaire_base', 0) or 0
        e.taux_commission = request.form.get('taux_commission', 0) or 0
        db.session.commit()
        flash('Employé mis à jour.', 'success')
        return redirect(url_for('rh.index'))
    return render_template('rh/form_employe.html', employe=e)

@rh_bp.route('/pointage', methods=['GET', 'POST'])
@login_required
def pointage():
    today = date.today()
    if request.method == 'POST':
        action = request.form.get('action')
        emp_id = int(request.form.get('employe_id'))
        presence = Presence.query.filter_by(employe_id=emp_id, date_jour=today).first()
        if action == 'checkin':
            if not presence:
                presence = Presence(employe_id=emp_id, date_jour=today, heure_entree=datetime.now())
                db.session.add(presence)
                flash('Check-in enregistré.', 'success')
            else:
                flash('Check-in déjà enregistré aujourd\'hui.', 'warning')
        elif action == 'checkout':
            if presence and not presence.heure_sortie:
                presence.heure_sortie = datetime.now()
                flash('Check-out enregistré.', 'success')
            else:
                flash('Check-out impossible.', 'warning')
        db.session.commit()
        return redirect(url_for('rh.pointage'))
    employes = Employe.query.filter_by(actif=True).order_by(Employe.nom).all()
    presences_today = {p.employe_id: p for p in Presence.query.filter_by(date_jour=today).all()}
    return render_template('rh/pointage.html', employes=employes, presences=presences_today, today=today)
