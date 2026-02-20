from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ─────────────────────────────────────────
#  PARAMÈTRES GARAGE
# ─────────────────────────────────────────
class GarageConfig(db.Model):
    __tablename__ = 'garage_config'
    id            = db.Column(db.Integer, primary_key=True)
    nom_garage    = db.Column(db.String(150), nullable=False, default='Duka Auto')
    slogan        = db.Column(db.String(255))
    adresse       = db.Column(db.Text)
    telephone     = db.Column(db.String(30))
    email         = db.Column(db.String(120))
    logo_filename = db.Column(db.String(255))
    devise        = db.Column(db.String(10), default='FBu')
    numero_nif    = db.Column(db.String(50))
    numero_rc     = db.Column(db.String(50))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─────────────────────────────────────────
#  UTILISATEURS
# ─────────────────────────────────────────
class Utilisateur(UserMixin, db.Model):
    __tablename__ = 'utilisateurs'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(30), default='technicien')
    nom_complet   = db.Column(db.String(150))
    telephone     = db.Column(db.String(30))
    actif         = db.Column(db.Boolean, default=True)
    derniere_connexion = db.Column(db.DateTime)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    employe       = db.relationship('Employe', backref='utilisateur', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def role_label(self):
        labels = {
            'admin': 'Administrateur',
            'manager': 'Manager',
            'technicien': 'Technicien',
            'comptable': 'Comptable',
            'receptionniste': 'Réceptionniste'
        }
        return labels.get(self.role, self.role)


# ─────────────────────────────────────────
#  CLIENTS
# ─────────────────────────────────────────
class Client(db.Model):
    __tablename__ = 'clients'
    id          = db.Column(db.Integer, primary_key=True)
    nom         = db.Column(db.String(100), nullable=False)
    prenom      = db.Column(db.String(100))
    telephone   = db.Column(db.String(30))
    telephone2  = db.Column(db.String(30))
    email       = db.Column(db.String(120))
    adresse     = db.Column(db.Text)
    quartier    = db.Column(db.String(100))
    ville       = db.Column(db.String(80), default='Bujumbura')
    type_client = db.Column(db.String(20), default='particulier')
    nom_entreprise = db.Column(db.String(150))
    nif_entreprise = db.Column(db.String(50))
    notes       = db.Column(db.Text)
    actif       = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    vehicules   = db.relationship('Vehicule', backref='client', lazy='dynamic')

    @property
    def nom_complet(self):
        if self.type_client == 'entreprise' and self.nom_entreprise:
            return self.nom_entreprise
        return f"{self.prenom or ''} {self.nom}".strip()

    @property
    def nb_vehicules(self):
        return self.vehicules.count()

    @property
    def nb_reparations(self):
        total = 0
        for v in self.vehicules:
            total += v.reparations.count()
        return total


# ─────────────────────────────────────────
#  VÉHICULES
# ─────────────────────────────────────────
class Vehicule(db.Model):
    __tablename__ = 'vehicules'
    id              = db.Column(db.Integer, primary_key=True)
    client_id       = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    immatriculation = db.Column(db.String(30), unique=True, nullable=False)
    marque          = db.Column(db.String(80))
    modele          = db.Column(db.String(80))
    annee           = db.Column(db.Integer)
    couleur         = db.Column(db.String(40))
    vin             = db.Column(db.String(50))
    kilometrage     = db.Column(db.Integer, default=0)
    carburant       = db.Column(db.String(20), default='essence')
    transmission    = db.Column(db.String(20), default='manuelle')
    notes           = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    reparations     = db.relationship('Reparation', backref='vehicule', lazy='dynamic')


# ─────────────────────────────────────────
#  RESSOURCES HUMAINES
# ─────────────────────────────────────────
class Employe(db.Model):
    __tablename__ = 'employes'
    id              = db.Column(db.Integer, primary_key=True)
    utilisateur_id  = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True)
    nom             = db.Column(db.String(100), nullable=False)
    prenom          = db.Column(db.String(100), nullable=False)
    poste           = db.Column(db.String(100))
    telephone       = db.Column(db.String(30))
    email           = db.Column(db.String(120))
    adresse         = db.Column(db.Text)
    date_naissance  = db.Column(db.Date)
    date_embauche   = db.Column(db.Date, default=date.today)
    numero_cnss     = db.Column(db.String(50))
    salaire_base    = db.Column(db.Numeric(15, 2), default=0)
    taux_commission = db.Column(db.Numeric(5, 2), default=0)
    actif           = db.Column(db.Boolean, default=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    presences       = db.relationship('Presence', backref='employe', lazy='dynamic')
    commissions     = db.relationship('Commission', backref='employe', lazy='dynamic')

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    @property
    def presences_mois(self):
        debut = date.today().replace(day=1)
        return self.presences.filter(Presence.date_jour >= debut).count()

    @property
    def total_commissions_mois(self):
        debut = date.today().replace(day=1)
        result = db.session.query(
            db.func.coalesce(db.func.sum(Commission.montant), 0)
        ).filter(
            Commission.employe_id == self.id,
            Commission.date_calcul >= debut
        ).scalar()
        return float(result)


class Presence(db.Model):
    __tablename__ = 'presences'
    id           = db.Column(db.Integer, primary_key=True)
    employe_id   = db.Column(db.Integer, db.ForeignKey('employes.id'), nullable=False)
    date_jour    = db.Column(db.Date, default=date.today, nullable=False)
    heure_entree = db.Column(db.DateTime)
    heure_sortie = db.Column(db.DateTime)
    statut       = db.Column(db.String(20), default='present')
    note         = db.Column(db.Text)

    __table_args__ = (db.UniqueConstraint('employe_id', 'date_jour', name='uq_presence_jour'),)

    @property
    def duree_heures(self):
        if self.heure_entree and self.heure_sortie:
            delta = self.heure_sortie - self.heure_entree
            return round(delta.total_seconds() / 3600, 2)
        return 0


class Commission(db.Model):
    __tablename__ = 'commissions'
    id            = db.Column(db.Integer, primary_key=True)
    employe_id    = db.Column(db.Integer, db.ForeignKey('employes.id'), nullable=False)
    reparation_id = db.Column(db.Integer, db.ForeignKey('reparations.id'), nullable=False)
    montant       = db.Column(db.Numeric(15, 2), nullable=False)
    taux_applique = db.Column(db.Numeric(5, 2))
    date_calcul   = db.Column(db.DateTime, default=datetime.utcnow)
    payee         = db.Column(db.Boolean, default=False)


# ─────────────────────────────────────────
#  FOURNISSEURS & STOCK
# ─────────────────────────────────────────
class Fournisseur(db.Model):
    __tablename__ = 'fournisseurs'
    id           = db.Column(db.Integer, primary_key=True)
    nom          = db.Column(db.String(150), nullable=False)
    contact      = db.Column(db.String(100))
    telephone    = db.Column(db.String(30))
    email        = db.Column(db.String(120))
    adresse      = db.Column(db.Text)
    type_fourn   = db.Column(db.String(20), default='local')
    pays_origine = db.Column(db.String(80))
    nif          = db.Column(db.String(50))
    actif        = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    pieces       = db.relationship('Piece', backref='fournisseur', lazy='dynamic')


class Piece(db.Model):
    __tablename__ = 'pieces'
    id             = db.Column(db.Integer, primary_key=True)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'))
    reference      = db.Column(db.String(80), unique=True, nullable=False)
    nom            = db.Column(db.String(200), nullable=False)
    description    = db.Column(db.Text)
    categorie      = db.Column(db.String(80))
    prix_achat     = db.Column(db.Numeric(15, 2), default=0)
    prix_vente     = db.Column(db.Numeric(15, 2), default=0)
    quantite_stock = db.Column(db.Integer, default=0)
    seuil_critique = db.Column(db.Integer, default=5)
    unite          = db.Column(db.String(20), default='pièce')
    actif          = db.Column(db.Boolean, default=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mouvements     = db.relationship('MouvementStock', backref='piece', lazy='dynamic')

    @property
    def stock_critique(self):
        return self.quantite_stock <= self.seuil_critique

    @property
    def marge(self):
        if float(self.prix_achat) > 0:
            return round((float(self.prix_vente) - float(self.prix_achat)) / float(self.prix_achat) * 100, 1)
        return 0


class MouvementStock(db.Model):
    __tablename__ = 'mouvements_stock'
    id             = db.Column(db.Integer, primary_key=True)
    piece_id       = db.Column(db.Integer, db.ForeignKey('pieces.id'), nullable=False)
    type_mvt       = db.Column(db.String(20), nullable=False)
    quantite       = db.Column(db.Integer, nullable=False)
    prix_unitaire  = db.Column(db.Numeric(15, 2))
    reference_doc  = db.Column(db.String(100))
    note           = db.Column(db.Text)
    date_mvt       = db.Column(db.DateTime, default=datetime.utcnow)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))


# ─────────────────────────────────────────
#  DEVIS
# ─────────────────────────────────────────
class Devis(db.Model):
    __tablename__ = 'devis'
    id             = db.Column(db.Integer, primary_key=True)
    vehicule_id    = db.Column(db.Integer, db.ForeignKey('vehicules.id'), nullable=False)
    technicien_id  = db.Column(db.Integer, db.ForeignKey('employes.id'))
    numero_devis   = db.Column(db.String(30), unique=True, nullable=False)
    statut         = db.Column(db.String(20), default='brouillon')
    # brouillon | envoye | accepte | refuse | expire
    date_devis     = db.Column(db.DateTime, default=datetime.utcnow)
    date_validite  = db.Column(db.Date)
    description_panne = db.Column(db.Text)
    montant_mo     = db.Column(db.Numeric(15, 2), default=0)
    montant_pieces = db.Column(db.Numeric(15, 2), default=0)
    montant_ht     = db.Column(db.Numeric(15, 2), default=0)
    taux_tva       = db.Column(db.Numeric(5, 2), default=18)
    montant_tva    = db.Column(db.Numeric(15, 2), default=0)
    montant_ttc    = db.Column(db.Numeric(15, 2), default=0)
    notes          = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    vehicule       = db.relationship('Vehicule', backref='devis')
    technicien     = db.relationship('Employe', backref='devis')
    lignes         = db.relationship('LigneDevis', backref='devis', lazy='dynamic', cascade='all, delete-orphan')
    reparation     = db.relationship('Reparation', backref='devis', uselist=False)

    def calculer_totaux(self):
        self.montant_pieces = sum(float(l.quantite) * float(l.prix_unitaire) for l in self.lignes)
        self.montant_ht = float(self.montant_mo) + float(self.montant_pieces)
        self.montant_tva = round(float(self.montant_ht) * float(self.taux_tva) / 100, 0)
        self.montant_ttc = float(self.montant_ht) + float(self.montant_tva)


class LigneDevis(db.Model):
    __tablename__ = 'lignes_devis'
    id            = db.Column(db.Integer, primary_key=True)
    devis_id      = db.Column(db.Integer, db.ForeignKey('devis.id'), nullable=False)
    piece_id      = db.Column(db.Integer, db.ForeignKey('pieces.id'))
    designation   = db.Column(db.String(200), nullable=False)
    quantite      = db.Column(db.Numeric(10, 2), default=1)
    prix_unitaire = db.Column(db.Numeric(15, 2), nullable=False)
    type_ligne    = db.Column(db.String(20), default='piece')
    # piece | main_oeuvre | service

    piece         = db.relationship('Piece')

    @property
    def sous_total(self):
        return float(self.quantite) * float(self.prix_unitaire)


# ─────────────────────────────────────────
#  CYCLE DE RÉPARATION
# ─────────────────────────────────────────
class Reparation(db.Model):
    __tablename__ = 'reparations'
    id                = db.Column(db.Integer, primary_key=True)
    vehicule_id       = db.Column(db.Integer, db.ForeignKey('vehicules.id'), nullable=False)
    technicien_id     = db.Column(db.Integer, db.ForeignKey('employes.id'))
    devis_id          = db.Column(db.Integer, db.ForeignKey('devis.id'))
    numero_or         = db.Column(db.String(30), unique=True, nullable=False)
    statut            = db.Column(db.String(30), default='reception')
    date_reception    = db.Column(db.DateTime, default=datetime.utcnow)
    date_diagnostic   = db.Column(db.DateTime)
    date_debut_trav   = db.Column(db.DateTime)
    date_fin_trav     = db.Column(db.DateTime)
    kilometrage_entree = db.Column(db.Integer)
    description_panne  = db.Column(db.Text)
    diagnostic         = db.Column(db.Text)
    observations       = db.Column(db.Text)
    montant_mo         = db.Column(db.Numeric(15, 2), default=0)
    montant_pieces     = db.Column(db.Numeric(15, 2), default=0)
    montant_ht         = db.Column(db.Numeric(15, 2), default=0)
    taux_tva           = db.Column(db.Numeric(5, 2), default=18)
    montant_tva        = db.Column(db.Numeric(15, 2), default=0)
    montant_total      = db.Column(db.Numeric(15, 2), default=0)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)

    technicien         = db.relationship('Employe', backref='reparations_tech')
    lignes_pieces      = db.relationship('LignePieceReparation', backref='reparation', lazy='dynamic', cascade='all, delete-orphan')
    facture            = db.relationship('Facture', backref='reparation', uselist=False)
    commissions        = db.relationship('Commission', backref='reparation', lazy='dynamic')

    def calculer_totaux(self):
        self.montant_pieces = sum(float(l.quantite) * float(l.prix_unitaire) for l in self.lignes_pieces)
        self.montant_ht = float(self.montant_mo) + float(self.montant_pieces)
        self.montant_tva = round(float(self.montant_ht) * float(self.taux_tva) / 100, 0)
        self.montant_total = float(self.montant_ht) + float(self.montant_tva)


class LignePieceReparation(db.Model):
    __tablename__ = 'lignes_pieces_reparation'
    id            = db.Column(db.Integer, primary_key=True)
    reparation_id = db.Column(db.Integer, db.ForeignKey('reparations.id'), nullable=False)
    piece_id      = db.Column(db.Integer, db.ForeignKey('pieces.id'))
    designation   = db.Column(db.String(200), nullable=False)
    quantite      = db.Column(db.Numeric(10, 2), default=1)
    prix_unitaire = db.Column(db.Numeric(15, 2), nullable=False)

    piece         = db.relationship('Piece', backref='lignes_reparation')

    @property
    def sous_total(self):
        return float(self.quantite) * float(self.prix_unitaire)


# ─────────────────────────────────────────
#  FACTURATION
# ─────────────────────────────────────────
class Facture(db.Model):
    __tablename__ = 'factures'
    id              = db.Column(db.Integer, primary_key=True)
    reparation_id   = db.Column(db.Integer, db.ForeignKey('reparations.id'), nullable=False, unique=True)
    numero_facture  = db.Column(db.String(30), unique=True, nullable=False)
    date_facture    = db.Column(db.DateTime, default=datetime.utcnow)
    montant_ht      = db.Column(db.Numeric(15, 2), default=0)
    taux_tva        = db.Column(db.Numeric(5, 2), default=18)
    montant_tva     = db.Column(db.Numeric(15, 2), default=0)
    montant_ttc     = db.Column(db.Numeric(15, 2), default=0)
    statut_paiement = db.Column(db.String(20), default='impayee')
    mode_paiement   = db.Column(db.String(30))
    date_paiement   = db.Column(db.DateTime)
    notes           = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────
#  COMPTABILITÉ
# ─────────────────────────────────────────
class EcritureComptable(db.Model):
    __tablename__ = 'ecritures_comptables'
    id             = db.Column(db.Integer, primary_key=True)
    date_ecriture  = db.Column(db.Date, default=date.today, nullable=False)
    type_ecriture  = db.Column(db.String(10), nullable=False)
    categorie      = db.Column(db.String(80))
    description    = db.Column(db.String(255), nullable=False)
    montant        = db.Column(db.Numeric(15, 2), nullable=False)
    reference      = db.Column(db.String(100))
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
