import firebase_admin
from firebase_admin import credentials, firestore, auth

def initialize_firebase():
    try:
        cred_path = r"C:\Users\anama\Downloads\movie-catalogo-firebase-adminsdk-fbsvc-b443ed4cf7.json"
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        print("Firebase inicializado correctamente")
        return firestore.client()
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        return None

db = initialize_firebase()
