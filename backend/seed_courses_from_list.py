from pymongo import MongoClient

MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'academic_tracker'
DEPARTMENT = 'AIDA'

COURSES = [
    ("PCP2", "Professional Coading Practice - II"),
    ("PCD3", "Professional Competency Development -III"),
    ("MATH3", "Mathematics  III"),
    ("NOSQL", "NOSQL Database with Mongo DB"),
    ("DAALAB", "Design and Analysis of Algorithm Laboratory"),
    ("PYLAB", "Hands on Python Laboratory"),
    ("CPPLAB", "Hands on C++ Laboratory"),
    ("COA", "Computer Organization and Architecture"),
    ("WEBTECH", "Web Technology"),
    ("WEBLAB", "Web Technology Lab"),
    ("DAA", "Design and Analysis of Algorithm"),
]


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    print("Clearing existing courses...")
    db.courses.delete_many({})

    docs = []
    for code, name in COURSES:
        docs.append({
            'course_code': code,
            'course_name': name,
            'credits': 3,
            'department': DEPARTMENT,
        })
    if docs:
        db.courses.insert_many(docs)

    print(f"Inserted {len(docs)} courses.")


if __name__ == "__main__":
    main()
