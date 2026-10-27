# Varicash — Loan EMI Tracker

A full-stack loan application tracker built with Django REST Framework, PostgreSQL 16, React, and Docker Compose.

## Features

- Apply for a loan with applicant details.
- Calculate EMI, total interest, and total payable on the backend.
- View loan applications, newest first.
- View a month-by-month repayment schedule.
- Approve or reject pending loan applications.
- Prevent status changes after a loan has been approved or rejected.
- Use decimal arithmetic and two-decimal monetary rounding.
- Persist loan data in PostgreSQL.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite |
| Web server / proxy | Nginx |
| Backend | Python, Django, Django REST Framework, Gunicorn |
| Database | PostgreSQL 16 |
| Containers | Docker, Docker Compose |

## Prerequisites

- Docker Desktop installed and running.
- Git, if cloning the repository.

Python and Node.js do not need to be installed separately to run the containerized application.

## Setup and Run

1. Clone the repository or download the project.
2. Open a terminal in the project root.
3. Create the local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

4. Update `.env` with suitable local values for the Django secret key and PostgreSQL password.
5. Build and start all services:

   ```powershell
   docker compose up --build
   ```

6. Open the application at:

   **http://localhost:8080**

The backend automatically runs database migrations at startup.

To stop the application, press `Ctrl+C` in the foreground terminal. Alternatively, run:

```powershell
docker compose down
```

The named PostgreSQL volume preserves database data when the containers are stopped or removed. Avoid `docker compose down -v` unless you intend to delete that data.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health/` | Health check and database connectivity |
| POST | `/api/loans/` | Create a loan application |
| GET | `/api/loans/` | List applications, newest first |
| GET | `/api/loans/{id}/` | Retrieve one application |
| PATCH | `/api/loans/{id}/status/` | Approve or reject a pending loan |
| GET | `/api/loans/{id}/schedule/` | Retrieve the monthly repayment schedule |

### Example: Create a Loan

Request to `POST /api/loans/`:

```json
{
  "applicant_name": "Rahul Sharma",
  "applicant_email": "rahul@example.com",
  "principal": "100000.00",
  "annual_interest_rate": "12.00",
  "tenure_months": 12
}
```

The backend calculates `emi`, `total_interest`, and `total_payable`. These calculated values, along with the loan status and creation time, are read-only to the client.

### Example: Update Loan Status

Request to `PATCH /api/loans/{id}/status/`:

```json
{
  "status": "APPROVED"
}
```

The supported status values are `APPROVED` and `REJECTED`. Only loans currently in `PENDING` status can be updated. Invalid input returns an appropriate HTTP 400 response.

### Repayment Schedule

The schedule endpoint returns each month's:

- `month`
- `emi`
- `principal_component`
- `interest_component`
- `remaining_balance`

The schedule is computed when requested; it is not stored in the database.

## EMI Calculation

The backend uses the following formula:

\[
EMI = \frac{P \times r \times (1+r)^n}{(1+r)^n-1}
\]

Where:

- `P` is the principal.
- `r` is the monthly interest rate, calculated as the annual interest rate divided by 1200.
- `n` is the tenure in months.

Python's `Decimal` type and Django's `DecimalField` are used for financial values, with monetary amounts rounded to two decimal places.

**Sanity check:** A principal of ₹1,00,000 at 12% annual interest for 12 months produces a regular EMI of ₹8,884.88.

The final installment is adjusted to absorb rounding differences so that the remaining balance is exactly ₹0.00.

## Docker Architecture

The application consists of three services:

- **Frontend:** Nginx serves the built React application and proxies `/api/` requests to the backend.
- **Backend:** Django REST Framework serves the API and connects to PostgreSQL using the Docker service hostname `db`.
- **Database:** PostgreSQL 16 stores loan applications in a named volume.

Architecture:

```text
Browser
   |
   v
localhost:8080
   |
   v
[ frontend: Nginx ]
   |
   | frontend_net
   v
[ backend: Django / Gunicorn ]
   |
   | backend_net
   v
[ db: PostgreSQL 16 ]
   |
   v
Named volume: postgres_data
```

### Network Isolation

Two custom Docker bridge networks are configured:

- `frontend_net`: contains the frontend and backend.
- `backend_net`: contains the backend and database.

The frontend cannot directly reach the database because it is not connected to `backend_net`. The backend is connected to both networks so it can receive proxied API requests and access PostgreSQL.

Only the frontend publishes a host port (`8080:80`). The backend and database do not publish host ports.

PostgreSQL has a health check, and the backend waits for the database to become healthy before starting. The backend runs database migrations automatically through its entrypoint script.

## Verification: Prove It Works

The following commands were run during local verification.

### 1. Docker services

Command:

```powershell
docker compose ps
```

Observed result: the `backend`, `db`, and `frontend` services were running. PostgreSQL reported `healthy`. Only the frontend published port `8080` to the host.

### 2. Docker networks

Command:

```powershell
docker network ls
```

Observed result: Docker created `varicash_backend_net` and `varicash_frontend_net`.

### 3. Backend network inspection

Command:

```powershell
docker network inspect varicash_backend_net
```

Observed result: the network contained `varicash-backend-1` and `varicash-db-1`, but not the frontend.

### 4. Frontend network inspection

Command:

```powershell
docker network inspect varicash_frontend_net
```

Observed result: the network contained `varicash-frontend-1` and `varicash-backend-1`, but not PostgreSQL.

### 5. Frontend-to-backend connectivity

Command:

```powershell
docker exec varicash-frontend-1 sh -c "wget -qO- http://backend:8000/api/health/"
```

Observed output:

```json
{"status":"ok"}
```

This confirms that the frontend container can reach the backend using the Docker service name.

### 6. Frontend-to-database isolation

Command:

```powershell
docker exec varicash-frontend-1 sh -c "wget -T 2 -qO- http://db:5432 || echo 'PASS: database is unreachable from frontend'"
```

Observed output:

```text
wget: bad address 'db:5432'
PASS: database is unreachable from frontend
```

The database hostname does not resolve from the frontend container because the frontend is not connected to the database's network.

### 7. Health check

Command:

```powershell
Invoke-RestMethod http://localhost:8080/api/health/
```

Observed result:

```text
status
------
ok
```

The health endpoint confirms that the API is running and can query the database.

### 8. EMI and repayment schedule

A loan was created with a principal of ₹1,00,000, annual interest rate of 12%, and tenure of 12 months.

Observed results:

- Regular EMI: ₹8,884.88
- Total payable: ₹1,06,618.53
- Total interest: ₹6,618.53
- Schedule length: 12 months
- Final remaining balance: ₹0.00

The final installment is adjusted for rounding, so the sum of the schedule's actual installments matches the total payable.

> These are local verification results. Repeat the commands on the final version of the repository before submitting.

## Configuration and Security

- Configuration is supplied through environment variables.
- `.env.example` contains example configuration values.
- `.env` is intended for local use and must not be committed.
- The backend connects to PostgreSQL through the service hostname `db`.
- The backend and database are not exposed directly on host ports.
- Authentication is not implemented because it is outside the assignment scope.

## Assumptions

- A loan can be approved or rejected only while its status is `PENDING`.
- The repayment schedule is generated on demand rather than stored.
- The final installment can differ slightly from the regular EMI to clear rounding differences.
- Authentication and user roles are not required for this assignment.

## Improvements With More Time

- Add unit tests for EMI calculations, schedule rounding, and validation.
- Register the loan model in Django admin.
- Add filtering by status, such as `/api/loans/?status=PENDING`.
- Add automated API and frontend tests.
- Run the backend container as a non-root user.
- Add structured logging and more detailed health monitoring.

## License

This project was created as a take-home hiring assignment.
