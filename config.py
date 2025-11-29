import os
from datetime import timedelta

class Config:
    """Configuration de base pour l'application"""
    
    # Sécurité
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Base de données
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///fraud_detection.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Mettre True en HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Modèle ML
    MODEL_PATH = os.environ.get('MODEL_PATH') or 'models/best_fraud_detection_model_20251031_2007.pkl'
    SCALER_PATH = os.environ.get('SCALER_PATH') or 'models/scaler.pkl'
    
    # Pagination
    TRANSACTIONS_PER_PAGE = 20
    
    # Limites
    MAX_TRANSACTION_AMOUNT = 1000000
    MIN_TRANSACTION_AMOUNT = 0.01


class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # En production, utilisez des variables d'environnement
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI')


class TestingConfig(Config):
    """Configuration pour les tests"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_fraud_detection.db'
    WTF_CSRF_ENABLED = False


# Dictionnaire des configurations
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}