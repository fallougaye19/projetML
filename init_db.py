"""
Script d'initialisation de la base de données PostgreSQL
Crée les tables et un utilisateur administrateur par défaut
"""

from dotenv import load_dotenv
import sys
import os

# Charger les variables d'environnement
load_dotenv()

# Importer après load_dotenv pour s'assurer que les variables sont chargées
from app import app, db, User

def init_database():
    """Initialise la base de données"""
    with app.app_context():
        print("🔄 Création des tables...")
        try:
            db.create_all()
            print("✅ Tables créées avec succès")
        except Exception as e:
            print(f"❌ Erreur lors de la création des tables : {e}")
            return False
        
        # Vérifier si un admin existe déjà
        admin = User.query.filter_by(role='admin').first()
        
        if not admin:
            print("\n👤 Création de l'utilisateur administrateur...")
            try:
                admin = User(
                    username='admin',
                    email='admin@fraud-detection.com',
                    role='admin'
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✅ Administrateur créé avec succès")
                print("\n" + "="*50)
                print("   IDENTIFIANTS ADMINISTRATEUR")
                print("="*50)
                print("   Username: admin")
                print("   Password: admin123")
                print("="*50)
                print("   ⚠️  IMPORTANT : Changez ce mot de passe !")
                print("="*50)
            except Exception as e:
                print(f"❌ Erreur lors de la création de l'admin : {e}")
                return False
        else:
            print("ℹ️  Un administrateur existe déjà")
        
        return True


def create_sample_users():
    """Crée des utilisateurs de test"""
    with app.app_context():
        test_users = [
            {'username': 'user1', 'email': 'user1@test.com', 'password': 'password123'},
            {'username': 'user2', 'email': 'user2@test.com', 'password': 'password123'},
            {'username': 'analyst', 'email': 'analyst@test.com', 'password': 'password123'},
        ]
        
        print("\n👥 Création des utilisateurs de test...")
        
        created_count = 0
        for user_data in test_users:
            try:
                if not User.query.filter_by(username=user_data['username']).first():
                    user = User(
                        username=user_data['username'],
                        email=user_data['email'],
                        role='user'
                    )
                    user.set_password(user_data['password'])
                    db.session.add(user)
                    print(f"   ✅ {user_data['username']} créé")
                    created_count += 1
                else:
                    print(f"   ⚠️  {user_data['username']} existe déjà")
            except Exception as e:
                print(f"   ❌ Erreur pour {user_data['username']}: {e}")
        
        try:
            db.session.commit()
            print(f"\n✅ {created_count} utilisateur(s) de test créé(s)")
        except Exception as e:
            print(f"❌ Erreur lors de la validation : {e}")
            db.session.rollback()


def reset_database():
    """Réinitialise complètement la base de données"""
    with app.app_context():
        print("\n" + "="*60)
        print("   ⚠️  ATTENTION : RÉINITIALISATION COMPLÈTE")
        print("="*60)
        print("   Cette action va supprimer TOUTES les données :")
        print("   - Tous les utilisateurs")
        print("   - Toutes les transactions")
        print("   - TOUT sera perdu définitivement !")
        print("="*60)
        
        response = input("\nÊtes-vous ABSOLUMENT sûr ? (tapez 'OUI' en majuscules) : ")
        
        if response == 'OUI':
            try:
                print("\n🔄 Suppression de toutes les tables...")
                db.drop_all()
                print("✅ Tables supprimées")
                
                print("\n🔄 Recréation des tables...")
                if init_database():
                    print("\n🔄 Création des utilisateurs de test...")
                    create_sample_users()
                    print("\n✅ Base de données réinitialisée avec succès")
                else:
                    print("\n❌ Échec de la réinitialisation")
            except Exception as e:
                print(f"\n❌ Erreur lors de la réinitialisation : {e}")
        else:
            print("❌ Opération annulée (vous deviez taper 'OUI' en majuscules)")


def show_stats():
    """Affiche les statistiques de la base de données"""
    with app.app_context():
        from app import Transaction
        
        try:
            users_count = User.query.count()
            transactions_count = Transaction.query.count()
            frauds_count = Transaction.query.filter_by(fraud_prediction=1).count()
            admins_count = User.query.filter_by(role='admin').count()
            
            print("\n" + "="*60)
            print("   📊 STATISTIQUES DE LA BASE DE DONNÉES")
            print("="*60)
            print(f"   👥 Utilisateurs         : {users_count}")
            print(f"      - Administrateurs    : {admins_count}")
            print(f"      - Utilisateurs normaux: {users_count - admins_count}")
            print(f"\n   💳 Transactions         : {transactions_count}")
            
            if transactions_count > 0:
                print(f"      - Fraudes détectées  : {frauds_count}")
                print(f"      - Légitimes          : {transactions_count - frauds_count}")
                fraud_rate = (frauds_count / transactions_count) * 100
                print(f"      - Taux de fraude     : {fraud_rate:.1f}%")
            
            print("="*60)
            
            # Détails sur les utilisateurs
            if users_count > 0:
                print("\n   📋 Liste des utilisateurs :")
                users = User.query.all()
                for user in users:
                    user_transactions = Transaction.query.filter_by(user_id=user.id).count()
                    role_icon = "👑" if user.role == 'admin' else "👤"
                    print(f"      {role_icon} {user.username} ({user.email}) - {user_transactions} transactions")
            
            print("\n" + "="*60)
            
        except Exception as e:
            print(f"\n❌ Erreur lors de la récupération des stats : {e}")


def check_connection():
    """Vérifie la connexion à la base de données"""
    print("\n🔍 Vérification de la connexion...")
    
    # Vérifier que DATABASE_URI est défini
    database_uri = os.getenv('DATABASE_URI')
    if not database_uri:
        print("❌ ERREUR : DATABASE_URI n'est pas défini")
        print("\n📋 Actions requises :")
        print("   1. Créer le fichier .env : cp .env.example .env")
        print("   2. Configurer DATABASE_URI dans .env")
        print("   3. Exemple : DATABASE_URI=postgresql://user:pass@localhost:5432/db")
        return False
    
    print(f"✅ DATABASE_URI trouvé")
    print(f"   Connexion : {database_uri.split('@')[1] if '@' in database_uri else 'format invalide'}")
    
    # Tester la connexion
    with app.app_context():
        try:
            # Essayer une requête simple
            from sqlalchemy import text
            result = db.session.execute(text('SELECT 1'))
            print("✅ Connexion à la base de données réussie")
            return True
        except Exception as e:
            print(f"❌ Échec de connexion à la base de données")
            print(f"   Erreur : {e}")
            print("\n📋 Vérifications à faire :")
            print("   1. PostgreSQL est-il démarré ?")
            print("   2. La base de données existe-t-elle ?")
            print("   3. L'utilisateur a-t-il les bons privilèges ?")
            print("   4. Les identifiants dans .env sont-ils corrects ?")
            return False


def show_help():
    """Affiche l'aide"""
    print("\n" + "="*60)
    print("   📚 AIDE - SCRIPT D'INITIALISATION")
    print("="*60)
    print("\n   Commandes disponibles :")
    print("\n   init          - Initialise la base de données")
    print("                   • Crée les tables")
    print("                   • Crée l'utilisateur admin")
    print("\n   reset         - Réinitialise complètement la BDD")
    print("                   • Supprime tout")
    print("                   • Recrée les tables")
    print("                   • Recrée admin et users de test")
    print("                   ⚠️  ATTENTION : Perte de données !")
    print("\n   create-users  - Crée des utilisateurs de test")
    print("                   • user1 / password123")
    print("                   • user2 / password123")
    print("                   • analyst / password123")
    print("\n   stats         - Affiche les statistiques")
    print("                   • Nombre d'utilisateurs")
    print("                   • Nombre de transactions")
    print("                   • Taux de fraude")
    print("\n   check         - Vérifie la connexion à la BDD")
    print("                   • Teste DATABASE_URI")
    print("                   • Vérifie PostgreSQL")
    print("\n   help          - Affiche cette aide")
    print("\n" + "="*60)
    print("\n   📋 Exemples d'utilisation :")
    print("\n   python init_db.py init")
    print("   python init_db.py stats")
    print("   python init_db.py create-users")
    print("   python init_db.py check")
    print("\n" + "="*60)


if __name__ == '__main__':
    print("="*60)
    print("   🐘 GESTIONNAIRE DE BASE DE DONNÉES POSTGRESQL")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\n❌ Erreur : Commande manquante")
        show_help()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'init':
        print("\n📦 Initialisation de la base de données...")
        if check_connection():
            if init_database():
                print("\n✅ Initialisation terminée avec succès !")
                print("\n💡 Prochaine étape : python app.py")
            else:
                print("\n❌ Échec de l'initialisation")
                sys.exit(1)
        else:
            sys.exit(1)
    
    elif command == 'reset':
        if check_connection():
            reset_database()
    
    elif command == 'create-users':
        if check_connection():
            create_sample_users()
    
    elif command == 'stats':
        if check_connection():
            show_stats()
    
    elif command == 'check':
        if check_connection():
            print("\n✅ Tout est OK ! Vous pouvez lancer l'application.")
        else:
            print("\n⚠️  Résolvez les problèmes avant de continuer.")
            sys.exit(1)
    
    elif command == 'help' or command == '--help' or command == '-h':
        show_help()
    
    else:
        print(f"\n❌ Commande inconnue : '{command}'")
        show_help()
        sys.exit(1)