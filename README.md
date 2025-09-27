# Flask + SQLite Backend

This is a minimal backend following the proposed plan with separated entities (students, professors) and simple auth.

## Structure

```
backend/
├── app.py
├── config.py
├── models.py
├── routes/
│   ├── __init__.py
│   ├── students.py
│   ├── professors.py
│   └── auth.py
├── services/
│   ├── student_service.py
│   ├── professor_service.py
│   └── auth_service.py
├── utils/
│   ├── db.py
│   └── validators.py
├── migrations/
│   └── .gitkeep
└── requirements.txt
```

## Quickstart (Windows / PowerShell)

- Create and activate a virtual environment

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

- Install dependencies

```
pip install -r backend/requirements.txt
```

- Run the app

```
python backend/app.py
```

The server runs at http://localhost:5000 and exposes:

- `GET /health`
- `GET/POST /students`, `PUT/DELETE /students/<id>`
- `GET/POST /professors`, `PUT/DELETE /professors/<id>`
- `POST /auth/register`, `POST /auth/login`
- Arduino management under `/arduino` (see below)

## Auth

- Register with:

```
POST /auth/register
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "Secret123!",
  "role": "admin"  // optional, defaults to "user"
}
```

- Login with:

```
POST /auth/login
{
  "identifier": "alice", // or alice@example.com
  "password": "Secret123!"
}
```

Response contains `access_token` (JWT). Include it in `Authorization: Bearer <token>` for protected routes if you add any later.

## Arduino Serial Management

Install the `pyserial` dependency (already in requirements):

```
pip install -r backend/requirements.txt
```

Endpoints (all under `/arduino`):

- `GET /arduino/ports` — List available serial ports and current connection status.
- `GET /arduino/status` — Current connection status (connected, port, baudrate).
- `POST /arduino/connect` — Connect to a port.
  - Body:
    ```json
    { "port": "COM3", "baudrate": 9600 }
    ```
- `POST /arduino/disconnect` — Cleanly close the serial connection.
- `GET /arduino/refresh` — Re-enumerate ports (same as listing again).

Notes:
- The Arduino is assumed to understand a simple line protocol. The backend sends: `CAPTURE <entity> <id>` and expects `OK`, `RETRY`, `FAIL`, or times out per attempt. Adjust in `utils/arduino.py` to match your firmware.
- After opening serial, we wait ~2 seconds to let the Arduino reset.

## Biometric Verification During Registration

When creating a `Student` or `Professor`, the backend performs fingerprint capture BEFORE committing the record:

Flow:
- Backend adds the new record and flushes to obtain the auto-incremented `id` (not committed yet).
- Backend sends `CAPTURE <entity> <id>` over serial.
- The device should reply with:
  - `OK` — verification success. The record is marked `fingerprint_verified = true` and COMMITTED.
  - `RETRY` or timeout — backend retries up to `fingerprint_retries` (default 3, can be provided in POST body).
  - `FAIL` — verification failed. The transaction is ROLLED BACK; nothing is saved.

Client request examples:

- Create student (with optional retry override):
  ```json
  {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "major": "CS",
    "fingerprint_retries": 3
  }
  ```

- Create professor:
  ```json
  {
    "name": "Dr. Smith",
    "email": "smith@example.com",
    "department": "Math",
    "fingerprint_retries": 3
  }
  ```

Frontend guidance:
- Provide UI to:
  - Select serial port (list ports), connect/disconnect, and refresh the list.
  - Show live status for fingerprint capture: success, failure, retry prompt.
  - Confirm when capture succeeded and data was saved.

## Schema changes note

This project uses `db.create_all()` to create tables. If you already created `app.db` before these changes (e.g., before adding `fingerprint_verified` fields), you will need to recreate the database or set up migrations. Quick options:

- Easiest (for development): stop the server, delete `backend/app.db`, and start again to recreate with the new columns.
- Production approach: integrate Flask-Migrate to handle schema migrations.

## Notes

- SQLite database file `app.db` will be created in `backend/` automatically on first run.
- CORS is enabled for all origins by default. Adjust in `config.py` if needed.
- Basic validation and unique email constraints are handled with SQLAlchemy and simple validators.
