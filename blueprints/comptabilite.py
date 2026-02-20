from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, EcritureComptable
from datetime import date
from sqlalchemy import func

compta_bp = Blueprint('comptabilite', __name__)

@compta_bp.route('/')
@login_required
def index():
    today = date.today()
    ecritures = EcritureComptable.query.order_by(
        EcritureComptable.date_ecriture.desc(),
        EcritureComptable.created_at.desc()
    ).limit(100).all()
    totaux = db.session.query(
        EcritureComptable.type_ecriture,
        func.sum(EcritureComptable.montant).label('total')
    ).filter(
        EcritureComptable.date_ecriture == today
    ).group_by(EcritureComptable.type_ecriture).all()
    totaux_dict = {t.type_ecriture: float(t.total) for t in totaux}
    return render_template('comptabilite/index.html',
        ecritures=ecritures,
        recettes_jour=totaux_dict.get('recette', 0),
        depenses_jour=totaux_dict.get('depense', 0),
        today=today
    )

@compta_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_ecriture():
    if request.method == 'POST':
        e = EcritureComptable(
            date_ecriture=date.fromisoformat(request.form.get('date_ecriture', str(date.today()))),
            type_ecriture=request.form['type_ecriture'],
            categorie=request.form.get('categorie', '').strip(),
            description=request.form['description'].strip(),
            montant=float(request.form['montant'] or 0),
            reference=request.form.get('reference', '').strip(),
            utilisateur_id=current_user.id
        )
        db.session.add(e)
        db.session.commit()
        flash('Écriture enregistrée.', 'success')
        return redirect(url_for('comptabilite.index'))
    return render_template('comptabilite/form_ecriture.html')
