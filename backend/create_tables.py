#!/usr/bin/env python3
"""
Script pour créer les tables de conversation dans la base de données
"""
import sys
import os

# Ajouter le répertoire parent au PATH pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_db, engine, Base
from sqlalchemy import text

def create_conversation_tables():
    """Crée les tables de conversation si elles n'existent pas"""
    try:
        print("Connexion à la base de données...")
        
        # Créer toutes les tables définies dans les modèles
        print("Création des tables...")
        Base.metadata.create_all(bind=engine)
        
        # Vérifier que les tables ont été créées
        with engine.connect() as conn:
            # Vérifier la table conversations
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'conversations'
                );
            """))
            conversations_exists = result.fetchone()[0]
            
            # Vérifier la table conversation_messages
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'conversation_messages'
                );
            """))
            messages_exists = result.fetchone()[0]
            
            print(f"Table 'conversations' existe: {conversations_exists}")
            print(f"Table 'conversation_messages' existe: {messages_exists}")
            
            if conversations_exists and messages_exists:
                print("✅ Toutes les tables de conversation ont été créées avec succès!")
                return True
            else:
                print("❌ Erreur: Certaines tables n'ont pas été créées")
                return False
                
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Script de création des tables de conversation")
    print("=" * 50)
    
    success = create_conversation_tables()
    
    if success:
        print("\n🎉 Migration terminée avec succès!")
        print("Vous pouvez maintenant utiliser l'historique des conversations.")
    else:
        print("\n💥 Échec de la migration!")
        print("Vérifiez les erreurs ci-dessus.")
        sys.exit(1)
