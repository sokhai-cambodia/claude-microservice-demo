# Claude Microservice Demo

A demo e-commerce backend built with three independent FastAPI microservices, each with its own PostgreSQL database, orchestrated via Docker Compose.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   auth-service  │     │ product-service  │     │  order-service  │
│   :8001         │◄────│   :8002         │◄────│   :8003         │
│                 │◄────┤                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                        │
    ┌────▼────┐             ┌────▼────┐             ┌────▼────┐
    │ auth-db │             │product  │             │ order-  │
    │(postgres)│            │   -db   │             │   db    │
    └─────────┘             └─────────┘             └─────────┘
```

**Service communication:**
- `product-service` and `order-service` call `auth-service /auth/verify` on every authenticated request
- `order-service` calls `product-service /products/{id}` to resolve prices when creating an order
- There are no shared databases — each service owns its data

## Services

### auth-service (port 8001)

Handles user registration, login, and JWT token issuance/verification.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Create a new user account |
| POST | `/auth/login` | No | Log in and receive a JWT token |
| GET | `/auth/me` | Bearer | Get current user profile |
| GET | `/auth/verify?token=...` | No | Verify a JWT and return its claims (used internally by other services) |

**Environment variables:**

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | AsyncPG connection string |
| `JWT_SECRET` | Secret key for signing JWTs — **change in production** |
| `JWT_ALGORITHM` | Algorithm (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL in minutes (default: `30`) |

---

### product-service (port 8002)

CRUD management for products. Listing and fetching are public; creating, updating, and deleting require a valid JWT.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/products/` | No | List all products |
| GET | `/products/{id}` | No | Get a single product |
| POST | `/products/` | Bearer | Create a product |
| PUT | `/products/{id}` | Bearer | Replace a product |
| DELETE | `/products/{id}` | Bearer | Delete a product |

**Environment variables:**

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | AsyncPG connection string |
| `AUTH_SERVICE_URL` | Base URL of auth-service (e.g. `http://auth-service:8001`) |

---

### order-service (port 8003)

Manages orders for the authenticated user. Prices are resolved at order-creation time by calling product-service.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/orders/` | Bearer | List all orders for the current user |
| GET | `/orders/{id}` | Bearer | Get a single order (must belong to current user) |
| POST | `/orders/` | Bearer | Create an order (resolves prices from product-service) |
| PATCH | `/orders/{id}/cancel` | Bearer | Cancel a pending order |

**Environment variables:**

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | AsyncPG connection string |
| `AUTH_SERVICE_URL` | Base URL of auth-service |
| `PRODUCT_SERVICE_URL` | Base URL of product-service (e.g. `http://product-service:8002`) |

---

## Data Models

### User (auth-service)
| Field | Type | Notes |
|-------|------|-------|
| `id` | int | Primary key |
| `username` | string | Unique |
| `email` | string | Unique |
| `hashed_password` | string | bcrypt |
| `is_active` | bool | Default: true |
| `created_at` | datetime | |

### Product (product-service)
| Field | Type | Notes |
|-------|------|-------|
| `id` | int | Primary key |
| `name` | string | |
| `description` | string | Optional |
| `price` | decimal(10,2) | Must be > 0 |
| `stock` | int | Must be >= 0, default: 0 |
| `created_at` | datetime | |
| `updated_at` | datetime | Auto-updated |

### Order / OrderItem (order-service)
| Field | Type | Notes |
|-------|------|-------|
| `id` | int | Primary key |
| `user_id` | int | From JWT `sub` claim |
| `status` | string | `pending` \| `confirmed` \| `cancelled` |
| `total_price` | decimal(10,2) | Sum of `unit_price × quantity` |
| `items` | list | Loaded via `selectin` |

| Field | Type | Notes |
|-------|------|-------|
| `id` | int | Primary key |
| `order_id` | int | FK → orders |
| `product_id` | int | No FK (cross-service) |
| `quantity` | int | Must be > 0 |
| `unit_price` | decimal(10,2) | Snapshotted at order creation |

---

## Getting Started

### Prerequisites
- Docker and Docker Compose

### Run all services

```bash
docker compose up --build
```

All three services start after their respective databases pass health checks.

### Interactive API docs

| Service | Swagger UI |
|---------|-----------|
| auth-service | http://localhost:8001/docs |
| product-service | http://localhost:8002/docs |
| order-service | http://localhost:8003/docs |

---

## Example Walkthrough

**1. Register a user**
```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "secret"}'
```

**2. Log in and capture the token**
```bash
TOKEN=$(curl -s -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret"}' | jq -r .access_token)
```

**3. Create a product**
```bash
curl -X POST http://localhost:8002/products/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Widget", "price": "9.99", "stock": 100}'
```

**4. Place an order**
```bash
curl -X POST http://localhost:8003/orders/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"product_id": 1, "quantity": 2}]}'
```

**5. Cancel an order**
```bash
curl -X PATCH http://localhost:8003/orders/1/cancel \
  -H "Authorization: Bearer $TOKEN"
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | FastAPI |
| ORM | SQLAlchemy 2 (async) |
| Database driver | asyncpg |
| Database | PostgreSQL 16 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| HTTP client | httpx (async) |
| Validation | Pydantic v2 |
| Container | Docker / Docker Compose |

---

## Production Notes

- Replace `JWT_SECRET: supersecretkey_changeme_in_prod` with a strong random secret.
- The `product_id` in `order_items` is a soft reference — there is intentionally no database-level foreign key across services.
- Token prices are snapshotted at order creation time; they do not change if the product price is later updated.
