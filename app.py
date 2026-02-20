import os
from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from config import Config
from models import db, Utilisateur, GarageConfig, Reparation, Piece, EcritureComptable
from datetime import date, datetime

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Veuillez vous connecter.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return Utilisateur.query.get(int(user_id))

    os.makedirs(app.config['LOGO_FOLDER'], exist_ok=True)

    @app.context_processor
    def inject_globals():
        cfg = GarageConfig.query.first()
        stats_sidebar = {
            'en_cours': Reparation.query.filter(
                Reparation.statut.in_(['reception','diagnostic','devis','en_cours'])
            ).count(),
            'critiques': Piece.query.filter(
                Piece.quantite_stock <= Piece.seuil_critique,
                Piece.actif == True
            ).count(),
        }
        return dict(garage_cfg=cfg, stats_sidebar=stats_sidebar)

    @app.template_filter('fbu')
    def format_fbu(value):
        try:
            return f"{float(value):,.0f} FBu".replace(",", " ")
        except:
            return "0 FBu"

    # ── ROUTES PRINCIPALES ──
    @app.route('/')
    @login_required
    def dashboard():
        today = date.today()
        stats = {
            'reparations_en_cours': Reparation.query.filter(
                Reparation.statut.in_(['reception','diagnostic','devis','en_cours'])
            ).count(),
            'pieces_critiques': Piece.query.filter(
                Piece.quantite_stock <= Piece.seuil_critique,
                Piece.actif == True
            ).count(),
            'recettes_jour': float(db.session.query(
                db.func.coalesce(db.func.sum(EcritureComptable.montant), 0)
            ).filter(
                EcritureComptable.type_ecriture == 'recette',
                EcritureComptable.date_ecriture == today
            ).scalar()),
            'depenses_jour': float(db.session.query(
                db.func.coalesce(db.func.sum(EcritureComptable.montant), 0)
            ).filter(
                EcritureComptable.type_ecriture == 'depense',
                EcritureComptable.date_ecriture == today
            ).scalar()),
        }
        reparations_recentes = Reparation.query.order_by(
            Reparation.created_at.desc()
        ).limit(8).all()
        pieces_critiques = Piece.query.filter(
            Piece.quantite_stock <= Piece.seuil_critique,
            Piece.actif == True
        ).order_by(Piece.quantite_stock).limit(5).all()
        return render_template('dashboard.html',
            stats=stats,
            reparations_recentes=reparations_recentes,
            pieces_critiques=pieces_critiques
        )

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            user = Utilisateur.query.filter_by(username=username, actif=True).first()
            if user and user.check_password(password):
                user.derniere_connexion = datetime.utcnow()
                db.session.commit()
                login_user(user, remember=request.form.get('remember') == 'on')
                flash(f'Bienvenue, {user.username} !', 'success')
                return redirect(request.args.get('next') or url_for('dashboard'))
            flash('Identifiants incorrects.', 'danger')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Vous êtes déconnecté.', 'info')
        return redirect(url_for('login'))

    @app.route('/parametres', methods=['GET', 'POST'])
    @login_required
    def parametres():
        cfg = GarageConfig.query.first()
        if not cfg:
            cfg = GarageConfig()
            db.session.add(cfg)
            db.session.commit()
        if request.method == 'POST':
            cfg.nom_garage  = request.form.get('nom_garage', cfg.nom_garage).strip()
            cfg.slogan      = request.form.get('slogan', '').strip()
            cfg.adresse     = request.form.get('adresse', '').strip()
            cfg.telephone   = request.form.get('telephone', '').strip()
            cfg.email       = request.form.get('email', '').strip()
            cfg.numero_nif  = request.form.get('numero_nif', '').strip()
            cfg.numero_rc   = request.form.get('numero_rc', '').strip()
            logo_file = request.files.get('logo')
            if logo_file and logo_file.filename:
                ext = logo_file.filename.rsplit('.', 1)[-1].lower()
                if ext in app.config['ALLOWED_EXTENSIONS']:
                    filename = secure_filename(f"logo_garage.{ext}")
                    logo_file.save(os.path.join(app.config['LOGO_FOLDER'], filename))
                    cfg.logo_filename = filename
                else:
                    flash('Format non autorisé.', 'warning')
            db.session.commit()
            flash('Paramètres enregistrés.', 'success')
            return redirect(url_for('parametres'))
        return render_template('parametres.html', cfg=cfg)

    @app.route('/uploads/logos/<filename>')
    def uploaded_logo(filename):
        return send_from_directory(app.config['LOGO_FOLDER'], filename)

    # ── BLUEPRINTS ──
    from blueprints.rh import rh_bp
    from blueprints.stock import stock_bp
    from blueprints.reparations import rep_bp
    from blueprints.comptabilite import compta_bp
    from blueprints.clients import clients
    from blueprints.users import users
    from blueprints.devis import devis_bp

    app.register_blueprint(rh_bp, url_prefix='/rh')
    app.register_blueprint(stock_bp, url_prefix='/stock')
    app.register_blueprint(rep_bp, url_prefix='/reparations')
    app.register_blueprint(compta_bp, url_prefix='/comptabilite')
    app.register_blueprint(clients, url_prefix='/clients')
    app.register_blueprint(users, url_prefix='/utilisateurs')
    app.register_blueprint(devis_bp, url_prefix='/devis')

    with app.app_context():
        db.create_all()
        _seed_initial_data()

    return app


def _seed_initial_data():
    if not Utilisateur.query.filter_by(username='admin').first():
        admin = Utilisateur(
            username='admin',
            email='admin@duka-auto.bi',
            nom_complet='Administrateur',
            role='admin',
            actif=True
        )
        admin.set_password('Admin2024!')
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin créé : admin / Admin2024!")
    if not GarageConfig.query.first():
        cfg = GarageConfig(nom_garage='Duka Auto', slogan='Votre partenaire automobile de confiance', devise='FBu')
        db.session.add(cfg)
        db.session.commit()


app = create_app()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
