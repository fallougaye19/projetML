from flask import Flask, request, jsonify, render_template
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
import hashlib
import os

app = Flask(__name__)

# ==============================
# 🔹 Fonction utilitaire : encodage stable
# ==============================
def stable_hash(value):
    """Encodage stable et déterministe pour les variables catégorielles."""
    if isinstance(value, str):
        return int(hashlib.sha256(value.encode()).hexdigest(), 16) % 1000
    return 0

# ==============================
# 🔹 Chargement du modèle et du scaler
# ==============================
MODEL_PATH = os.path.join("models", "best_fraud_detection_model_20251031_2007.pkl")
SCALER_PATH = os.path.join("models", "scaler.pkl")

try:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("✅ Modèle et scaler chargés avec succès.")
except Exception as e:
    print(f"❌ Erreur lors du chargement : {e}")
    model, scaler = None, None

# ==============================
# 🔹 Page d’accueil
# ==============================
@app.route('/')
def home():
    return render_template('index.html')

# ==============================
# 🔹 API de prédiction
# ==============================
@app.route('/api/predict', methods=['POST'])
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

        # Vérification des champs
        for field in required_fields:
            if field not in data or data[field] in [None, ""]:
                return jsonify({'error': f'Champ manquant ou vide : {field}'}), 400

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

        # Mise à l’échelle
        X_scaled = scaler.transform(df)

        # Prédiction
        probas = model.predict_proba(X_scaled)[0]
        classes = model.classes_
        index_fraud = np.where(classes == 1)[0][0] if 1 in classes else 1
        probability = float(probas[index_fraud])
        prediction = int(np.argmax(probas))

        # Interprétation du risque
        if probability >= 0.7:
            risk = "Élevé"
        elif probability >= 0.4:
            risk = "Modéré"
        else:
            risk = "Faible"

        result = {
            "timestamp": datetime.now().isoformat(),
            "fraud_prediction": prediction,
            "fraud_probability": probability,
            "risk_level": risk,
            "status": "🚨 FRAUDE DÉTECTÉE" if prediction == 1 else "✅ Transaction légitime",
            "confidence": f"{probability*100:.1f}%"
        }

        print(f"[INFO] {result['status']} (proba={probability:.2f})")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Erreur dans la prédiction : {e}")
        return jsonify({'error': str(e)}), 500

# ==============================
# 🔹 Endpoint de vérification
# ==============================
@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy' if model and scaler else 'unhealthy',
        'model_loaded': model is not None,
        'scaler_loaded': scaler is not None,
        'timestamp': datetime.now().isoformat()
    })


# ==============================
# ❌ Pas de app.run() pour Render !
# Render utilisera : gunicorn app:app
# ==============================
