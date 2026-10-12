# PyHunt Shop

A Django online shop with a browser interface, session cart,
customer accounts, product reviews and a REST API with JWT authentication.

## Technologies

- Python 3.14
- Django and Django REST Framework
- SimpleJWT
- PostgreSQL 17
- Docker Compose
- drf-spectacular for Swagger/OpenAPI
- pytest and pytest-django
- uv for dependencies and locking

Dependencies are declared in `pyproject.toml` and locked in `uv.lock`.

## Features

- Product catalog with search, category and price filters, pagination,
  and sorting by price, popularity and creation date.
- Product details, reviews and calculated average ratings.
- Session cart with quantity changes, removal, totals and stock checks.
- Checkout with delivery details and three simulated payment methods:
  debit card, digital wallet and cash on delivery.
- Customer registration, login, logout and access to personal orders.
- Transactional order creation and cancellation.
- Django Admin for users, categories, products, orders and reviews.
- Public product API and protected customer order API.
- Swagger documentation and JWT authentication.

Popularity counts purchased quantities from paid, shipped and delivered
orders. Pending and cancelled orders are excluded.

## Run with Docker

Install Git and Docker with Docker Compose. Start Docker Desktop.

Clone the checkout branch:

```bash
git clone --branch feature/checkout https://github.com/Viktoria-DS/M3PyHuntersProject.git
cd M3PyHuntersProject
```

Copy the environment template.

Windows:

```bat
copy .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

The template contains empty values. Fill the actual `.env` file:

| Variable | Value |
|----------|-------|
| SECRET_KEY | A generated random key |
| DEBUG | True for local development |
| ALLOWED_HOSTS | localhost,127.0.0.1 |
| POSTGRES_HOST | postgres |
| POSTGRES_DB | Your chosen database name |
| POSTGRES_USER | Your chosen database username |
| POSTGRES_PASSWORD | Your chosen database password |

Generate a key once:

```bash
docker run --rm python:3.14-slim-bookworm python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copy the printed value into `SECRET_KEY`.
Keep actual environment files out of Git.

Start the application:

```bash
docker compose up --build
```

Django waits for PostgreSQL's health check, applies migrations and starts
the development server.

Open:

- Website: http://localhost:8000/
- Admin: http://localhost:8000/admin/
- Swagger: http://localhost:8000/api/docs/
- OpenAPI schema: http://localhost:8000/api/schema/

This configuration runs the application for local development.

### Initial data

In another terminal, create an administrator:

```bash
docker compose exec web python manage.py createsuperuser
```

Sign in to the admin panel and create categories and products.
Products need a price, image, active status and available stock.

Customers can register at:

http://localhost:8000/users/register/

### Migrations and stopping

Migrations run automatically during startup. To apply them manually:

```bash
docker compose exec web python manage.py migrate
```

To inspect their status:

```bash
docker compose exec web python manage.py showmigrations
```

Stop the containers:

```bash
docker compose down
```

The `pgdata` volume stores PostgreSQL data.
The `media` volume stores uploaded images.

## Order and review rules

New orders have pending status. Supported transitions are:

```text
pending → paid
pending → cancelled
paid → shipped
paid → cancelled
shipped → delivered
```

Delivered and cancelled are final statuses.

Customers can cancel only their own pending orders.
Administrators manage the remaining transitions.

Orders are retained after cancellation. Stock is restored once;
repeated cancellation is rejected.

Order creation, order items and stock reduction share one transaction.
An invalid position or insufficient stock rejects the entire order.

Item prices are copied from the database at checkout and remain unchanged
when product prices change later.

Website checkout stores the submitted name, phone, city and address
together in `Order.shipping_address` as a delivery snapshot.

Customers can publish one review per product after a delivered purchase.
Ratings must be integers from 1 to 5.

Average ratings are calculated from reviews rather than stored in
the product. Products without reviews return null ratings in the API.

## REST API

| Method | Endpoint | Authentication |
|--------|----------|----------------|
| GET | /api/products/ | Public |
| GET | /api/products/{id}/ | Public |
| POST | /api/token/ | Username and password |
| POST | /api/token/refresh/ | Refresh token in request body |
| GET | /api/orders/ | JWT |
| POST | /api/orders/ | JWT |
| GET | /api/orders/{id}/ | JWT |
| POST | /api/orders/{id}/cancel/ | JWT |

Product lists support `category`, `min_price`, `max_price`, `search`
and `page` query parameters. `category` is a category ID.

For example:

```text
GET /api/products/?min_price=5&max_price=20&page=1
```

Product lists contain six products per page.

The cart belongs to the browser interface and is stored in the session.
API clients submit order items directly.

### JWT and Swagger

1. Register a customer or use an existing account.
2. Open Swagger and execute POST `/api/token/` with that account's
   username and password.
3. The response contains an access token and a refresh token.
4. Click Authorize and paste only the access token.
   Swagger adds the Bearer authentication prefix.
5. Use the protected order endpoints.

Other API clients send the access token in the Authorization header
using the Bearer scheme.

To obtain a new access token, execute POST `/api/token/refresh/`
with the returned refresh token in the `refresh` request field.

### Create an order

First retrieve products and choose an existing active product with stock.
In this example, replace product ID 1 with the actual returned ID.

```json
{
  "items": [
    {
      "product_id": 1,
      "quantity": 1
    }
  ],
  "shipping_address": "Example street 12, Berlin",
  "payment_method": "cod"
}
```

Submit this body to POST `/api/orders/`.

Successful creation returns HTTP 201.
Invalid order data returns HTTP 400.

The server determines the owner, prices, total and initial status.
Client-supplied owner, user, price, total_price and status fields
are rejected.

Customers can retrieve and cancel only their own orders.
PUT, PATCH and DELETE are unavailable for orders.

Successful cancellation returns HTTP 200.
Repeated cancellation returns HTTP 400.

## Tests

With the containers running:

```bash
docker compose exec web uv run --locked --group dev pytest -v
```

The command installs the development dependencies when needed.
Tests use a separate PostgreSQL test database.

Tests are collected from the root `tests.py` file and cover:

- Order creation, validation, price snapshots and rollback.
- Cancellation, ownership, stock restoration and status transitions.
- Cart operations and checkout.
- Registration, login, logout and customer order access.
- Catalog filtering, sorting, pagination and popularity.
- Review eligibility, duplicates, ratings and average calculations.
- Product and order APIs, JWT and documentation.

To run tests locally, install uv and use:

```bash
uv sync --locked
uv run --locked --group dev pytest -v
```

Local execution reads `.env.local`.
Use the same database credentials as `.env`, but set
`POSTGRES_HOST=localhost` while PostgreSQL is available on port 5432.

## Project structure

```text
api/             REST API serializers, views and routes
config/          Django settings and main URL configuration
orders/          Cart, checkout, models and shared order services
products/        Catalog, product models and product pages
reviews/         Review models, forms and submission views
users/           Accounts and authentication
templates/       Shared templates
static/          CSS, JavaScript and static images
tests.py         Automated tests
pytest.ini       Test discovery and Django configuration
Dockerfile       Application image
docker-compose.yml
.env.example     Environment variable template
pyproject.toml   Dependencies
uv.lock          Locked dependency versions
```

The website and API reuse `orders/services.py` for order creation
and cancellation.



