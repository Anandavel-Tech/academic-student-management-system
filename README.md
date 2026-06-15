# Acadimi

Acadimi is a Flask application backed by MongoDB.

## Run on Windows PowerShell

From the project root:

```powershell
py -3.14 -m venv .venv314
.\.venv314\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python backend\app.py
```

Open <http://127.0.0.1:5000> in a browser.

Default admin login:

- Username: `admin`
- Password: `12345678`

MongoDB is optional for launching the application. Without a local MongoDB
server at `mongodb://localhost:27017`, the app starts with temporary mock data.
For persistent users, courses, students, and marks, start MongoDB before
starting the Flask app.
