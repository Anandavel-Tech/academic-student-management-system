import bcrypt
from pymongo import MongoClient

MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'academic_tracker'

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '12345678'


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    existing = db.users.find_one({'username': ADMIN_USERNAME})
    if existing:
        print(f"Admin user '{ADMIN_USERNAME}' already exists.")
        return

    hashed = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt())
    db.users.insert_one({
        'username': ADMIN_USERNAME,
        'password': hashed,
        'role': 'admin'
    })
    print(f"Created admin user '{ADMIN_USERNAME}' with default password.")


if __name__ == '__main__':
    main()
