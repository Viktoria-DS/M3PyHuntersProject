# PyHunt Shop

A Django online shop with the Hop & Barley interface, a session cart,
customer accounts, product reviews and a REST API with JWT authentication.

## Technologies

- Python 3.14
- Django and Django REST Framework
- PostgreSQL 17
- SimpleJWT
- drf-spectacular for Swagger/OpenAPI
- Docker Compose
- pytest and pytest-django
- uv for dependency management

Dependencies are declared in `pyproject.toml` and locked in `uv.lock`.

## Features

- Product catalog with search, category and price filters, pagination,
  and sorting by price, popularity and creation date.
- Product details, customer reviews and calculated average ratings.
- Session cart with quantity changes, removal, totals and stock checks.
- Checkout with delivery details and three simulated payment methods:
  debit card, digital wallet and cash on delivery.
- Registration, login, POST logout and customer accounts.
- Personal order history, order details and cancellation.
- Transactional order creation and cancellation.
- Django Admin for users, categories, products, orders and reviews.
- Public product API and protected customer order API.
- JWT login and token refresh.
- Password change and password reset through the website and REST API.
- Swagger documentation and automated tests.

Popularity counts purchased quantities from paid, shipped and delivered
orders. Pending and cancelled orders are excluded.

## Run with Docker

Install Git and Docker with Docker Compose. Start Docker Desktop.

Clone the repository:

```bash
git clone --branch master https://github.com/Viktoria-DS/M3PyHuntersProject.git
cd M3PyHuntersProject
```

### Environment variables

Copy `.env.example` to `.env`.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

The environment template contains empty values. Fill them in the actual
`.env` file:

| Variable | Value |
|----------|-------|
| SECRET_KEY | A generated random key |
| DEBUG | True for local development |
| ALLOWED_HOSTS | localhost,127.0.0.1 |
| POSTGRES_HOST | postgres |
| POSTGRES_DB | Your chosen database name |
| POSTGRES_USER | Your chosen database username |
| POSTGRES_PASSWORD | Your chosen database password |

Generate a secret key:

```bash
docker run --rm python:3.14-slim-bookworm python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copy the printed value into `SECRET_KEY`.

Actual environment files are excluded from Git.

### Start the application

```bash
docker compose up --build
```

The application waits for PostgreSQL to become healthy, applies migrations
and starts the Django development server.

Open:

- [Website](http://localhost:8000/)
- [Admin](http://localhost:8000/admin/)
- [Swagger](http://localhost:8000/api/docs/)
- [OpenAPI schema](http://localhost:8000/api/schema/)

This Docker configuration is intended for local development.

Source code is copied into the application image. After editing Python,
templates or static files, run `docker compose up --build` again to rebuild
the image with the changes.

### Initial data

In another terminal, create an administrator:

```bash
docker compose exec web python manage.py createsuperuser
```

Sign in to the admin panel and create categories and products.
Products need a price, image, active status and available stock.

Customers can register through the
[registration page](http://localhost:8000/users/register/).

### Migrations

Migrations run automatically during startup. To apply them manually:

```bash
docker compose exec web python manage.py migrate
```

To inspect their status:

```bash
docker compose exec web python manage.py showmigrations
```

### Logs and stopping

Display application logs:

```bash
docker compose logs -f web
```

Stop the containers:

```bash
docker compose down
```

The `pgdata` volume preserves PostgreSQL data.
The `media` volume preserves uploaded images.

## Order and review rules

### Order creation

Checkout requires an authenticated customer.

The browser cart is stored in the session and preserved when the customer
logs in.

The website and API reuse `orders/services.py` for order creation and
cancellation.

Order creation, order items and stock reduction share one database
transaction. Invalid items or insufficient stock reject the entire order.

The server determines product prices, the order total, owner and initial
status. Item prices remain snapshots of the prices at checkout.

The customer relationship is named `Order.owner`.

Website checkout stores the submitted name, phone, city and address
together in `Order.shipping_address` as a delivery snapshot.

The cart is cleared after successful website checkout.

Payment methods are simulated:

| Value | Method |
|-------|--------|
| debit | Debit Card |
| wallet | Digital Wallet |
| cod | Cash On Delivery |

### Statuses and cancellation

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

Orders are retained after cancellation. Stock is restored once.
Repeated cancellation is rejected.

### Reviews

Customers can publish one review per product after a delivered purchase.

Ratings must be integers from 1 to 5.

Average ratings are calculated from reviews. Products without reviews
return `null` for their average rating in the API.

## REST API

| Method | Endpoint | Authentication |
|--------|----------|----------------|
| GET | /api/products/ | Public |
| GET | /api/products/{id}/ | Public |
| POST | /api/token/ | Username and password |
| POST | /api/token/refresh/ | Refresh token in the request body |
| GET | /api/orders/ | JWT |
| POST | /api/orders/ | JWT |
| GET | /api/orders/{id}/ | JWT |
| POST | /api/orders/{id}/cancel/ | JWT |
| POST | /api/change_password/ | JWT |
| POST | /api/reset_password/ | Public |
| POST | /api/reset_password_confirm/ | Public |

The browser cart is session-based.
API clients submit order items directly.

### Product filtering

Product lists support these query parameters:

| Parameter | Purpose |
|-----------|---------|
| category | Filter by category ID |
| min_price | Minimum price |
| max_price | Maximum price |
| search | Search product names and descriptions |
| page | Page number |

Example:

```text
GET /api/products/?min_price=5&max_price=20&page=1
```

API product lists contain six products per page.

### JWT and Swagger

1. Register a customer or use an existing account.
2. Open Swagger and execute POST `/api/token/` with the account's
   username and password.
3. The response contains an access token and a refresh token.
4. Click **Authorize** and paste only the access token.
   Swagger adds the Bearer authentication prefix.
5. Execute the protected order or password-change endpoints.

Other API clients send the access token in the `Authorization` header
using the Bearer scheme.

To obtain a new access token, execute POST `/api/token/refresh/`.
Pass the previously returned refresh token in the `refresh` field.

### Create an order

First retrieve products and choose an existing active product with stock.

Submit this JSON body to POST `/api/orders/`.
Use an actual product ID from the product list:

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

Successful creation returns HTTP 201.
Invalid order data returns HTTP 400.

Client-supplied fields such as `owner`, `user`, `price`, `total_price`
and `status` are rejected.

### Retrieve and cancel orders

Customers can list, retrieve and cancel only their own orders.

To cancel a pending order, execute POST `/api/orders/{id}/cancel/`
using its ID. No request body is needed.

Successful cancellation returns HTTP 200.
Repeated cancellation returns HTTP 400.

PUT, PATCH and DELETE are unavailable for orders.

## Password management

### Website

Authenticated customers can change their password from the
[account page](http://localhost:8000/users/account/).

The password-change form requires the current password and two matching
new passwords.

Customers who have forgotten their password can use the **Forgot password?**
link on the login page.

The reset process consists of:

1. Submitting the account's email address.
2. Receiving a reset link.
3. Opening the link and entering a new password twice.
4. Signing in with the new password.

### Email during local development

The project uses Django's console email backend.
Reset emails are printed in the application logs.

Read them with:

```bash
docker compose logs -f web
```

Submit a reset request using the email address of an existing active
account with a usable password.

The response deliberately uses the same message for known and unknown
email addresses.

A long reset URL may appear in the console with quoted-printable soft
line breaks. When copying it, remove `=` followed by a line break and
remove Docker log prefixes.

### Password-change API

Execute POST `/api/change_password/` with JWT authentication.

The request requires:

| Field | Value |
|-------|-------|
| old_password | The current password |
| new_password1 | The chosen new password |
| new_password2 | The same new password |

Django checks the current password, matching new passwords and configured
password validators.

Success returns HTTP 200:

```json
{
  "detail": "Password changed successfully."
}
```

An incorrect current password or invalid new password returns HTTP 400.
An unauthenticated request returns HTTP 401.

To verify the change, request a new JWT pair through `/api/token/`
using the new password.

### Password-reset request API

Execute POST `/api/reset_password/` without authentication:

```json
{
  "email": "buyer@example.com"
}
```

Use the email address of the account being tested.

For a valid email input, the response is HTTP 200:

```json
{
  "detail": "If an account exists with this email address, you will receive password-reset instructions."
}
```

For an eligible account, a reset email is printed in the application logs.

### Password-reset confirmation API

Read the latest reset email. Its URL contains two values after
`password_reset_confirm/`: `uidb64` and `token`.

Execute POST `/api/reset_password_confirm/` without authentication.

The request requires:

| Field | Value |
|-------|-------|
| uidb64 | The encoded user ID from the reset link |
| token | The token from the same reset link |
| new_password1 | The chosen new password |
| new_password2 | The same new password |

Keep the UID and token unchanged when copying them.

The API validates the user, reset token and new password before saving.

Success returns HTTP 200:

```json
{
  "detail": "Your password was successfully changed!"
}
```

Invalid or expired tokens return HTTP 400.
A token cannot be reused after it has successfully changed the password.

Verify the result by signing in or requesting JWT tokens with the
new password.

## Tests

With the containers running:

```bash
docker compose exec web uv run --locked --group dev pytest -v
```

uv installs the development dependencies when needed.
Tests use a separate PostgreSQL test database.

Tests are collected from the root `tests.py` file and cover:

- Order creation, validation, price snapshots and rollback.
- Cancellation, ownership, stock restoration and status transitions.
- Cart operations and checkout.
- Registration, login, logout and customer order access.
- Catalog filtering, sorting, pagination and popularity.
- Review eligibility, duplicates, ratings and average calculations.
- Product and order APIs, JWT and API documentation.
- Password change, password reset and invalid reset tokens.

### Run tests locally

Install Python 3.14 and uv, then run:

```bash
uv sync --locked --group dev
uv run --locked --group dev pytest -v
```

Local Django execution reads `.env.local`.

Copy the values from `.env` into `.env.local`, but set
`POSTGRES_HOST=localhost`.

PostgreSQL must be running and available on port 5432.

## Additional features

- Account profile editing: edit account details on the account page,
  save and reload the page to verify the changes.
- Password change and password reset: available through both the website
  and REST API, with verification steps described above.
- uv dependency management: dependencies are locked in `uv.lock` and
  installed through the documented Docker and local test commands.

## Project structure

```text
api/                 REST API serializers, views and routes
config/              Django settings and main URL configuration
orders/              Cart, checkout, models and shared order services
products/            Catalog, product models and product pages
reviews/             Review models, forms and submission views
users/               Accounts and authentication
templates/           Shared templates
static/              CSS, JavaScript and static images
tests.py             Automated tests
pytest.ini           Test discovery and Django configuration
Dockerfile           Application image
docker-compose.yml   Application and PostgreSQL services
.env.example         Environment variable template
pyproject.toml       Dependencies
uv.lock              Locked dependency versions
```