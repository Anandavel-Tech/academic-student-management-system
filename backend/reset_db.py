import bcrypt
from pymongo import MongoClient

MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'academic_tracker'

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '12345678'


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    print(f"Dropping collections in {DB_NAME}...")
    for name in db.list_collection_names():
        db.drop_collection(name)
        print(f"  Dropped {name}")

    print("Recreating admin user...")
    hashed = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt())
    db.users.insert_one({
        'username': ADMIN_USERNAME,
        'password': hashed,
        'role': 'admin'
    })
    print("Done. Admin credentials: username='admin', password='12345678'")


if __name__ == '__main__':
    main()
