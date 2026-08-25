import sys
from app import create_app
from database.models import db

def reset_database():
    print("Initializing Flask Application context...")
    app = create_app()
    
    with app.app_context():
        print("WARNING: This will permanently delete ALL data in the connected database.")
        confirmation = input("Are you absolutely sure you want to proceed? Type 'yes' to continue: ")
        
        if confirmation.lower() != 'yes':
            print("Operation aborted. No changes were made.")
            sys.exit(0)
            
        print("Dropping all existing tables...")
        db.drop_all()
        
        print("Recreating fresh tables...")
        db.create_all()
        
        print("✅ Database successfully wiped and reset!")
        print("You can now test registration on a completely clean slate.")

if __name__ == '__main__':
    reset_database()
