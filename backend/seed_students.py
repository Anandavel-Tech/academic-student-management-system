import bcrypt
from pymongo import MongoClient

MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'academic_tracker'

DEPARTMENT = 'AIDA'
DEFAULT_STUDENT_PASSWORD = 'password123'


def generate_students(start=1, end=51):
    """Yield student dicts for roll numbers E0324001..E0324051.

    i = 1  -> E0324001
    i = 51 -> E0324051
    """
    for i in range(start, end + 1):
        # 1 -> 001, 2 -> 002, ..., 51 -> 051
        suffix = f"{i:03d}"
        roll_no = f"E0324{suffix}"  # E0324001 .. E0324051
        email = f"{roll_no.lower()}@sriher.edu.in"
        name = f"Student {roll_no}"
        yield {
            'name': name,
            'email': email,
            'roll_no': roll_no,
            'department': DEPARTMENT,
        }


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    students_coll = db.students
    users_coll = db.users

    # Optional cleanup: remove any previously seeded range so we can reseed cleanly
    # Remove students whose roll_no starts with E0324 and length is 7 (old ones were 6)
    students_coll.delete_many({'roll_no': {'$regex': '^E0324'}})
    users_coll.delete_many({'username': {'$regex': '^E0324'}})

    hashed_pw = bcrypt.hashpw(DEFAULT_STUDENT_PASSWORD.encode('utf-8'), bcrypt.gensalt())

    created_students = 0
    created_users = 0

    for student in generate_students():
        # Skip if student with same roll_no already exists
        existing_student = students_coll.find_one({'roll_no': student['roll_no']})
        if existing_student:
            print(f"Student {student['roll_no']} already exists, skipping student insert")
        else:
            students_coll.insert_one(student)
            created_students += 1
            print(f"Inserted student {student['roll_no']}")

        # Ensure corresponding user exists (username = roll_no)
        existing_user = users_coll.find_one({'username': student['roll_no']})
        if existing_user:
            print(f"User for {student['roll_no']} already exists, skipping user insert")
        else:
            users_coll.insert_one({
                'username': student['roll_no'],
                'password': hashed_pw,
                'role': 'student',
            })
            created_users += 1
            print(f"Created user account for {student['roll_no']}")

    print("\nSummary:")
    print(f"  Students inserted: {created_students}")
    print(f"  User accounts created: {created_users}")
    print(f"  Default password for all new students: {DEFAULT_STUDENT_PASSWORD}")


if __name__ == '__main__':
    main()
