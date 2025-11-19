# Clean Architecture FastAPI

A production-ready FastAPI application implementing **Clean Architecture** (Hexagonal/Onion Architecture) with strict dependency rules, comprehensive testing, and modern Python best practices.

## Overview

This project demonstrates how to build a scalable, maintainable FastAPI application using Clean Architecture principles. The architecture enforces separation of concerns through four distinct layers, ensuring that business logic remains independent of frameworks, databases, and external services.

### Key Features

- **Clean Architecture** - Four-layer architecture with enforced dependency rules
- **Repository Pattern** - Abstract data access with swappable implementations
- **Unit of Work Pattern** - Transactional consistency across multiple repository operations
- **Dependency Injection** - Loose coupling through interface-based design
- **JWT Authentication** - Secure auth with access/refresh token rotation
- **Async/Await** - Full async support with SQLAlchemy 2.0+ and asyncpg
- **Type Safety** - Complete type annotations with mypy validation
- **Comprehensive Testing** - Unit and integration tests with 95%+ coverage
- **Database Migrations** - Alembic for version-controlled schema changes

## Architecture

```
┌─────────────────────────────────────────┐
│   Presentation Layer (FastAPI)          │  ← HTTP/API
├─────────────────────────────────────────┤
│   Application Layer (Use Cases)         │  ← Business Workflows
├─────────────────────────────────────────┤
│   Infrastructure Layer (Implementations) │  ← Database, Security
├─────────────────────────────────────────┤
│   Domain Layer (Business Logic)         │  ← Entities, Interfaces
└─────────────────────────────────────────┘
```

**Dependency Rule**: Outer layers depend on inner layers, never the reverse.

### Layer Breakdown

- **Domain** (`app/domain/`) - Pure business logic, entities, repository interfaces
- **Application** (`app/application/`) - Use case orchestration, DTOs, application services
- **Infrastructure** (`app/infrastructure/`) - Database models, repository implementations, security
- **Presentation** (`app/presentation/`) - FastAPI routers, HTTP handlers, API schemas

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 14+**
- **pip** or **poetry** for dependency management

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd clean-architecture-fastapi
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file and update with your settings:

```bash
cp .env.example .env
```

Edit `.env` and configure:

```env
# Application
SECRET_KEY=your-secret-key-at-least-32-characters-long
ENVIRONMENT=dev

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cleanarch_db
DB_USER=postgres
DB_PASSWORD=yourpassword
```

### 5. Setup Database

Create the PostgreSQL database:

```bash
createdb cleanarch_db
```

Run migrations:

```bash
alembic upgrade head
```

## Running the Application

### Development Server

```bash
fastapi dev app/main.py
```

Or using uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Health Check
```
GET /
```

### Authentication
```
POST   /api/v1/auth/login       # Login with email/password
POST   /api/v1/auth/refresh     # Refresh access token
POST   /api/v1/auth/logout      # Logout and revoke tokens
GET    /api/v1/auth/me          # Get current user (requires auth)
```

### Users
```
POST   /api/v1/users/           # Create new user
GET    /api/v1/users/{user_id}  # Get user by ID
PUT    /api/v1/users/{user_id}  # Update user
DELETE /api/v1/users/{user_id}  # Delete user
```

### Example: Create User

```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "John Doe",
    "password": "SecurePass123!"
  }'
```

### Example: Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

## Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html --cov-report=term
```

View coverage report: `open htmlcov/index.html`

### Run Specific Test Types

```bash
# Unit tests only (fast, no database)
pytest -m unit

# Integration tests (with database)
pytest -m integration

# Specific test file
pytest tests/unit/test_user_service.py -v
```

### Test Structure

- **Unit Tests** (`tests/unit/`) - Test business logic with in-memory fakes
- **Integration Tests** (`tests/integration/`) - Test with real database
- **Fakes** (`tests/fakes/`) - Lightweight test doubles for interfaces

## Database Migrations

### Create Migration

```bash
alembic revision --autogenerate -m "description of changes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

### View Migration History

```bash
alembic history
```

## Code Quality

### Format Code

```bash
black app/ tests/
```

### Lint Code

```bash
ruff check app/ tests/
```

### Type Check

```bash
mypy app/
```

## Project Structure

```
app/
├── domain/                    # Domain Layer (Core Business Logic)
│   ├── entities/              # Business entities (User, etc.)
│   ├── repositories/          # Repository interfaces
│   ├── services/              # Domain service interfaces
│   └── exceptions/            # Domain exceptions
├── application/               # Application Layer (Use Cases)
│   ├── services/              # Application services
│   ├── dtos/                  # Data Transfer Objects
│   └── exceptions/            # Application exceptions
├── infrastructure/            # Infrastructure Layer (Implementations)
│   ├── persistence/           # Database models and session
│   ├── repositories/          # Repository implementations
│   ├── security/              # Password hashing, JWT
│   └── config/                # Configuration and settings
├── presentation/              # Presentation Layer (API)
│   ├── api/v1/                # API version 1 routers
│   ├── dependencies.py        # DI composition root
│   └── error_codes.py         # API error codes
└── main.py                    # Application entry point

tests/
├── unit/                      # Unit tests (with fakes)
├── integration/               # Integration tests (with DB)
└── fakes/                     # Test doubles
```

## Development Guidelines

### Adding a New Feature

1. **Domain Layer**: Define entity and repository interface
2. **Application Layer**: Create service and DTOs
3. **Infrastructure Layer**: Implement repository
4. **Presentation Layer**: Add API endpoints
5. **Database**: Create and apply migration
6. **Tests**: Write unit and integration tests

### Dependency Rule

Always respect the dependency direction:
- Domain → No dependencies
- Application → Domain only
- Infrastructure → Domain (implements interfaces)
- Presentation → Application + Infrastructure

**Never** import from outer layers into inner layers.

## Security

- **Password Hashing**: Argon2 (industry standard)
- **Token Strategy**: JWT with refresh token rotation
- **Token Expiry**: Access tokens (15 min), Refresh tokens (7 days)
- **CORS**: Configured for development (update for production)

## Configuration

All settings are in `app/infrastructure/config/settings.py`:

- Database connection
- JWT settings (secret, algorithm, expiry)
- CORS configuration
- Environment-specific settings

## Production Considerations

Before deploying to production:

1. **Replace in-memory token storage** with Redis (see `dependencies.py`)
2. **Configure CORS** for your frontend domain
3. **Use environment variables** for all secrets
4. **Enable HTTPS** and secure cookies
5. **Set up logging** and monitoring
6. **Configure rate limiting**
7. **Use a production ASGI server** (Gunicorn + Uvicorn workers)

### Production Deployment Example

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

## Contributing

1. Follow the Clean Architecture principles
2. Write tests for new features
3. Run code quality checks before committing
4. Update documentation as needed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [Alembic](https://alembic.sqlalchemy.org/) - Database migrations
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [Argon2](https://argon2-cffi.readthedocs.io/) - Password hashing
