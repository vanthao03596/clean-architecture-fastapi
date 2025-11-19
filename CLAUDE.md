# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI application implementing **Clean Architecture** (also known as Hexagonal Architecture or Onion Architecture) with strict dependency rules, Repository pattern, and Unit of Work pattern. The architecture enforces that dependencies point INWARD - outer layers depend on inner layers, never the reverse.

## Architecture Layers

The codebase is organized into four concentric layers, from innermost to outermost:

### 1. Domain Layer (`app/domain/`)
- **Purpose**: Core business logic, completely framework-agnostic
- **Contains**: Entities, repository interfaces, domain services interfaces, domain exceptions
- **Dependencies**: NONE - this layer has zero external dependencies
- **Key principle**: Pure Python classes with business rules and validations

**Example**: `User` entity (`app/domain/entities/user.py`) validates email format and name requirements without knowing about databases or HTTP.

### 2. Application Layer (`app/application/`)
- **Purpose**: Use case orchestration and business workflows
- **Contains**: Application services, DTOs, application exceptions
- **Dependencies**: Only depends on Domain layer abstractions
- **Key principle**: Services depend on interfaces (e.g., `IUnitOfWork`, `IPasswordHasher`), not implementations

**Example**: `UserService` (`app/application/services/user_service.py`) orchestrates user creation by calling repositories and domain services through their interfaces.

### 3. Infrastructure Layer (`app/infrastructure/`)
- **Purpose**: Concrete implementations of domain interfaces
- **Contains**: Database models, repository implementations, security implementations, configuration
- **Dependencies**: Depends on Domain layer (implements its interfaces)
- **Key principle**: Implements abstractions defined in the domain layer

**Example**: `UserRepository` (`app/infrastructure/repositories/user_repository_impl.py`) implements `IUserRepository` using SQLAlchemy.

### 4. Presentation Layer (`app/presentation/`)
- **Purpose**: HTTP API and external interface
- **Contains**: FastAPI routers, dependencies (composition root), exception handlers
- **Dependencies**: Depends on Application and Infrastructure layers
- **Key principle**: Translates HTTP requests to application service calls

**Example**: User router (`app/presentation/api/v1/users.py`) receives HTTP requests and delegates to `UserService`.

## Key Patterns

### Unit of Work Pattern
- **Interface**: `IUnitOfWork` (`app/domain/repositories/unit_of_work.py`)
- **Implementation**: `UnitOfWork` (`app/infrastructure/repositories/unit_of_work_impl.py`)
- **Purpose**: Manages database transactions and provides access to all repositories within a transactional boundary
- **Usage**: Services receive a `uow_factory` callable that creates UoW instances, ensuring each operation gets its own transaction

```python
async with self._uow_factory() as uow:
    user = await uow.users.get_by_id(user_id)
    # ... business logic ...
    await uow.commit()
```

### Repository Pattern
- **Base Interface**: `IRepository[T]` (`app/domain/repositories/base.py`)
- **Entity-specific Interface**: `IUserRepository` extends `IRepository[User]`
- **Purpose**: Abstracts data persistence, allowing domain and application layers to be database-agnostic

### Dependency Injection
- **Composition Root**: `app/presentation/dependencies.py` is where ALL concrete implementations are wired up
- **Pattern**: Inner layers define interfaces, outer layers provide implementations
- **Testing**: Use fakes from `tests/fakes/` directory (e.g., `FakePasswordHasher`, `FakeUnitOfWork`)

### Domain Entity Validation
Entities validate their own invariants in `__post_init__` and domain methods:
- **Structural violations**: Raise `InvalidEntityStateException` (entity cannot exist)
- **Business rule violations**: Raise `BusinessRuleViolationException` (operation not allowed)

## Database & Migrations

**Database**: PostgreSQL with async support (asyncpg)

### Alembic Commands
```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Revert last migration
alembic downgrade -1

# View migration history
alembic history
```

**Note**: Alembic is configured to use sync driver. Update `alembic.ini` line 87 with your database URL if needed.

## Running the Application

### Development Server
```bash
# Run with auto-reload
fastapi dev app/main.py

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Setup
Copy `.env.example` to `.env` and configure:
- `SECRET_KEY`: Must be at least 32 characters (required)
- `DB_*`: Database connection parameters
- `ENVIRONMENT`: Set to `dev`, `test`, or `prod`

All settings are defined in `app/infrastructure/config/settings.py`.

## Testing

### Run Tests
```bash
# All tests
pytest

# Unit tests only (fast, no database)
pytest -m unit

# Integration tests (use database)
pytest -m integration

# With coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_user_service.py -v
```

### Test Structure
- **Unit tests** (`tests/unit/`): Test business logic in isolation using fakes
- **Integration tests** (`tests/integration/`): Test full workflows with real database
- **Fakes** (`tests/fakes/`): In-memory implementations of interfaces for testing
  - `FakeUnitOfWork`: In-memory transaction management
  - `FakePasswordHasher`: Deterministic password hashing
  - `FakeTokenService`: Token generation without JWT overhead

### Writing Tests
Use fakes instead of mocks when possible. Fakes are real implementations that behave correctly but use in-memory storage:

```python
service = UserService(
    uow_factory=lambda: FakeUnitOfWork(),
    password_hasher=FakePasswordHasher()
)
```

## Code Quality

### Linting & Formatting
```bash
# Format code with Black
black app/ tests/

# Lint with Ruff
ruff check app/ tests/

# Type check with mypy
mypy app/
```

## Exception Handling Strategy

The application uses a **hierarchical exception system** with just 5 global handlers:

1. `ApplicationError` - base class for all application exceptions (user not found, etc.)
2. `DomainException` - base class for all domain exceptions (validation errors, etc.)
3. `RequestValidationError` - Pydantic validation errors
4. `SQLAlchemyError` - database errors
5. `Exception` - catch-all for unexpected errors

**Key principle**: Don't create handlers for specific exceptions. Instead, inherit from `ApplicationError` or `DomainException` and use the `error_code` field to differentiate (see `app/presentation/error_codes.py`).

## Adding New Features

### Adding a New Entity (e.g., Product)

1. **Domain Layer** (`app/domain/`):
   - Create entity: `entities/product.py`
   - Create repository interface: `repositories/product_repository.py`
   - Update `IUnitOfWork` to include `products: IProductRepository`

2. **Application Layer** (`app/application/`):
   - Create DTOs: `dtos/product_dto.py`
   - Create service: `services/product_service.py`
   - Add exceptions if needed in `exceptions/exceptions.py`

3. **Infrastructure Layer** (`app/infrastructure/`):
   - Create SQLAlchemy model: `persistence/models/product_model.py`
   - Create repository implementation: `repositories/product_repository_impl.py`
   - Update `UnitOfWork.__aenter__` to instantiate `ProductRepository`

4. **Presentation Layer** (`app/presentation/`):
   - Create router: `api/v1/products.py`
   - Add dependency function in `dependencies.py`
   - Register router in `main.py`

5. **Database**:
   - Create migration: `alembic revision --autogenerate -m "create products table"`
   - Apply: `alembic upgrade head`

### Dependency Rule Enforcement
**NEVER** violate the dependency rule:
- Domain layer must NOT import from application, infrastructure, or presentation
- Application layer must NOT import from infrastructure or presentation
- Infrastructure and presentation can depend on inner layers

If you find yourself needing to import from an outer layer, you're likely missing an abstraction (interface) in an inner layer.

## Authentication & Security

- **Password Hashing**: Argon2 (via `Argon2PasswordHasher`)
- **Token Strategy**: JWT with refresh token rotation (Auth0-style)
- **Token Storage**: In-memory (dev) - replace with Redis for production (see `get_token_repository` in `dependencies.py`)
- **Protected Endpoints**: Use `Depends(get_current_user)` for authentication

## API Structure

All endpoints are versioned under `/api/v1/`:
- `POST /api/v1/users/` - Create user
- `GET /api/v1/users/{user_id}` - Get user
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user
- `POST /api/v1/auth/login` - Login (get tokens)
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout (revoke tokens)
- `GET /api/v1/auth/me` - Get current user (requires auth)

Health check: `GET /` (returns app status and version)
