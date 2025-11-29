from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
import hashlib
import os
from functools import wraps

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# Configuration depuis .env
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'votre-cle-secrete-changez-moi')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ==============================
# 📊 MODÈLES DE BASE DE DONNÉES
# ==============================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')  # user, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Données de transaction
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)
    house_type_id = db.Column(db.Integer)
    contact_availability_id = db.Column(db.Integer)
    home_country = db.Column(db.String(100))
    account_no = db.Column(db.String(50))
    card_expiry_date = db.Column(db.String(10))
    transaction_amount = db.Column(db.Float)
    transaction_country = db.Column(db.String(100))
    large_purchase = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    cif = db.Column(db.String(50))
    transaction_currency_code = db.Column(db.String(10))
    
    # Résultats de prédiction
    fraud_prediction = db.Column(db.Integer)
    fraud_probability = db.Column(db.Float)
    risk_level = db.Column(db.String(20))
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'transaction_amount': self.transaction_amount,
            'transaction_country': self.transaction_country,
            'fraud_prediction': self.fraud_prediction,
            'fraud_probability': self.fraud_probability,
            'risk_level': self.risk_level,
            'status': '🚨 FRAUDE' if self.fraud_prediction == 1 else '✅ LÉGITIME'
        }


# ==============================
# 🔐 GESTION DES UTILISATEURS
# ==============================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Accès administrateur requis', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ==============================
# 🔹 FONCTION UTILITAIRE
# ==============================

def stable_hash(value):
    """Encodage stable pour les variables catégorielles."""
    if isinstance(value, str):
        return int(hashlib.sha256(value.encode()).hexdigest(), 16) % 1000
    return 0


# ==============================
# 🔹 CHARGEMENT DU MODÈLE
# ==============================

MODEL_PATH = os.getenv('MODEL_PATH', 'models/best_fraud_detection_model_20251031_2007.pkl')
SCALER_PATH = os.getenv('SCALER_PATH', 'models/scaler.pkl')

try:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("✅ Modèle et scaler chargés avec succès.")
except Exception as e:
    print(f"❌ Erreur lors du chargement : {e}")
    model, scaler = None, None


# ==============================
# 🌐 ROUTES D'AUTHENTIFICATION
# ==============================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if User.query.filter_by(username=username).first():
            if request.is_json:
                return jsonify({'error': 'Nom d\'utilisateur déjà pris'}), 400
            flash('Nom d\'utilisateur déjà pris', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            if request.is_json:
                return jsonify({'error': 'Email déjà utilisé'}), 400
            flash('Email déjà utilisé', 'danger')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'message': 'Compte créé avec succès'}), 201
        
        flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            if request.is_json:
                return jsonify({'message': 'Connexion réussie'}), 200
            flash('Connexion réussie !', 'success')
            return redirect(url_for('dashboard'))
        
        if request.is_json:
            return jsonify({'error': 'Identifiants invalides'}), 401
        flash('Identifiants invalides', 'danger')
        return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnexion réussie', 'info')
    return redirect(url_for('login'))


# ==============================
# 🏠 ROUTES PRINCIPALES
# ==============================

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/predict')
@login_required
def predict_page():
    return render_template('index.html')


@app.route('/history')
@login_required
def history():
    return render_template('history.html')


# ==============================
# 📊 API DE STATISTIQUES
# ==============================

@app.route('/api/stats')
@login_required
def get_stats():
    user_transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    
    total = len(user_transactions)
    frauds = sum(1 for t in user_transactions if t.fraud_prediction == 1)
    legitimate = total - frauds
    
    total_amount = sum(t.transaction_amount for t in user_transactions)
    fraud_amount = sum(t.transaction_amount for t in user_transactions if t.fraud_prediction == 1)
    
    risk_distribution = {
        'Élevé': sum(1 for t in user_transactions if t.risk_level == 'Élevé'),
        'Modéré': sum(1 for t in user_transactions if t.risk_level == 'Modéré'),
        'Faible': sum(1 for t in user_transactions if t.risk_level == 'Faible')
    }
    
    # Transactions par jour (7 derniers jours)
    from collections import defaultdict
    daily_transactions = defaultdict(lambda: {'total': 0, 'frauds': 0})
    
    for t in user_transactions:
        date_key = t.timestamp.strftime('%Y-%m-%d')
        daily_transactions[date_key]['total'] += 1
        if t.fraud_prediction == 1:
            daily_transactions[date_key]['frauds'] += 1
    
    # Top 5 pays
    country_stats = defaultdict(lambda: {'total': 0, 'frauds': 0})
    for t in user_transactions:
        country_stats[t.transaction_country]['total'] += 1
        if t.fraud_prediction == 1:
            country_stats[t.transaction_country]['frauds'] += 1
    
    top_countries = sorted(
        country_stats.items(),
        key=lambda x: x[1]['total'],
        reverse=True
    )[:5]
    
    return jsonify({
        'overview': {
            'total': total,
            'frauds': frauds,
            'legitimate': legitimate,
            'fraud_rate': round(frauds / total * 100, 1) if total > 0 else 0,
            'total_amount': round(total_amount, 2),
            'fraud_amount': round(fraud_amount, 2)
        },
        'risk_distribution': risk_distribution,
        'daily_transactions': dict(daily_transactions),
        'top_countries': [{'country': k, 'stats': v} for k, v in top_countries]
    })


@app.route('/api/transactions')
@login_required
def get_transactions():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.timestamp.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'transactions': [t.to_dict() for t in transactions.items],
        'total': transactions.total,
        'pages': transactions.pages,
        'current_page': page
    })


# ==============================
# 🔮 API DE PRÉDICTION
# ==============================

@app.route('/api/predict', methods=['POST'])
@login_required
def predict():
    try:
        if model is None or scaler is None:
            return jsonify({'error': 'Modèle non disponible'}), 500

        data = request.get_json()
        required_fields = [
            'Gender','Age','HouseTypeID','ContactAvaliabilityID','HomeCountry',
            'AccountNo','CardExpiryDate','TransactionAmount','TransactionCountry',
            'LargePurchase','ProductID','CIF','TransactionCurrencyCode'
        ]

        for field in required_fields:
            if field not in data or data[field] in [None, ""]:
                return jsonify({'error': f'Champ manquant : {field}'}), 400

        # Préparation des données
        df = pd.DataFrame([{
            'Gender': 1 if str(data['Gender']).upper() in ['M', 'MALE', 'HOMME'] else 0,
            'Age': float(data['Age']),
            'HouseTypeID': int(data['HouseTypeID']),
            'ContactAvaliabilityID': int(data['ContactAvaliabilityID']),
            'HomeCountry': stable_hash(str(data['HomeCountry'])),
            'AccountNo': int(data['AccountNo']),
            'CardExpiryDate': int(data['CardExpiryDate']),
            'TransactionAmount': float(data['TransactionAmount']),
            'TransactionCountry': stable_hash(str(data['TransactionCountry'])),
            'LargePurchase': int(data['LargePurchase']),
            'ProductID': int(data['ProductID']),
            'CIF': int(data['CIF']),
            'TransactionCurrencyCode': stable_hash(str(data['TransactionCurrencyCode']))
        }])

        X_scaled = scaler.transform(df)
        probas = model.predict_proba(X_scaled)[0]
        classes = model.classes_
        index_fraud = np.where(classes == 1)[0][0] if 1 in classes else 1
        probability = float(probas[index_fraud])
        prediction = int(np.argmax(probas))

        if probability >= 0.7:
            risk = "Élevé"
        elif probability >= 0.4:
            risk = "Modéré"
        else:
            risk = "Faible"

        # Enregistrement dans la base de données
        transaction = Transaction(
            user_id=current_user.id,
            gender=data['Gender'],
            age=data['Age'],
            house_type_id=data['HouseTypeID'],
            contact_availability_id=data['ContactAvaliabilityID'],
            home_country=data['HomeCountry'],
            account_no=str(data['AccountNo']),
            card_expiry_date=str(data['CardExpiryDate']),
            transaction_amount=data['TransactionAmount'],
            transaction_country=data['TransactionCountry'],
            large_purchase=data['LargePurchase'],
            product_id=data['ProductID'],
            cif=str(data['CIF']),
            transaction_currency_code=data['TransactionCurrencyCode'],
            fraud_prediction=prediction,
            fraud_probability=probability,
            risk_level=risk
        )
        
        db.session.add(transaction)
        db.session.commit()

        result = {
            "id": transaction.id,
            "timestamp": transaction.timestamp.isoformat(),
            "fraud_prediction": prediction,
            "fraud_probability": probability,
            "risk_level": risk,
            "status": "🚨 FRAUDE DÉTECTÉE" if prediction == 1 else "✅ Transaction légitime",
            "confidence": f"{probability*100:.1f}%"
        }

        print(f"[INFO] {result['status']} - User: {current_user.username}")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Erreur : {e}")
        return jsonify({'error': str(e)}), 500


# ==============================
# 🔧 ADMINISTRATION
# ==============================

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    users = User.query.all()
    all_transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(100).all()
    
    return render_template('admin.html', users=users, transactions=all_transactions)


@app.route('/models-evaluation')
@login_required
def models_evaluation():
    return render_template('models_evaluation.html')


@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy' if model and scaler else 'unhealthy',
        'model_loaded': model is not None,
        'scaler_loaded': scaler is not None,
        'timestamp': datetime.now().isoformat()
    })


# ==============================
# 🚀 INITIALISATION
# ==============================

@app.before_request
def create_tables():
    if not hasattr(app, '_tables_created'):
        db.create_all()
        
        # Créer un admin par défaut si aucun utilisateur n'existe
        if User.query.count() == 0:
            admin = User(
                username='admin',
                email='admin@fraud-detection.com',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Utilisateur admin créé (admin/admin123)")
        
        app._tables_created = True


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)