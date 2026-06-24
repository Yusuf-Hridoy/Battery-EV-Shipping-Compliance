# BatteryShip — Project Documentation

## What is this project?

BatteryShip is a web application that helps small businesses and logistics teams classify lithium batteries and sodium-ion batteries for international shipping. Based on the user's input, the system determines the correct UN number, packing instruction, transport section, and other dangerous-goods requirements. It then generates an IATA-compliant **Shipper's Declaration PDF** and provides AI-powered explanations of the classification.

The application covers:
- Lithium-ion and lithium-metal batteries
- Sodium-ion batteries
- Batteries packed alone, with equipment, or contained in equipment
- E-bikes, e-scooters, and EV battery packs
- Air, sea, and road transport modes

---

## How the project was made

The project was built using an iterative, phase-based approach:

1. **Phase 1 — Classification Engine**: A deterministic rules engine was built to map battery specifications (chemistry, packaging, watt-hours, lithium content, transport mode) to the correct UN classification under IATA DGR, IMDG, and ADR regulations.
2. **Phase 2 — Authentication & User Management**: User registration and login were added with JWT-based authentication, password hashing, and role/plan-based usage limits.
3. **Phase 3 — API & Frontend**: REST API endpoints were exposed through FastAPI routers, and a frontend SPA was built with plain HTML, CSS, and JavaScript.
4. **Phase 4 — PDF & AI Explanations**: ReportLab was integrated to generate Shipper's Declaration PDFs, and Google Gemini was added to explain classifications and answer user questions.

The project is structured as a traditional 3-layer web application with clear separation between routes, business logic, and data access.

---

## Project Structure

```
Battery-EV-Shipping-Compliance/
├── main.py                 # FastAPI app entry point, lifespan, route mounting
├── database.py             # Async SQLAlchemy engine, session, and DB helpers
├── models.py               # SQLAlchemy ORM models
├── schemas.py              # Pydantic request/response schemas
├── alembic/                # Database migration files
│   ├── env.py              # Alembic async configuration
│   └── versions/           # Migration scripts
├── routers/                # HTTP route handlers
│   ├── auth.py             # Registration, login, current user
│   ├── billing.py          # Checkout, webhooks, subscription status
│   ├── classify.py         # Classification, history, options, AI explain
│   └── documents.py        # PDF generation, regulation updates
├── services/               # Core business logic
│   ├── auth.py             # Password/JWT utilities and plan limits
│   ├── billing.py          # Lemon Squeezy checkout and webhook handling
│   ├── classifier.py       # UN classification engine
│   ├── gemini.py           # Google Gemini AI integration
│   ├── pdf_generator.py    # Shipper's Declaration PDF generator
│   └── reset.py            # Monthly document counter reset job
├── static/                 # Frontend assets
│   ├── index.html          # Landing page with auth modal
│   ├── app.html            # Main application SPA
│   └── style.css           # Design system and UI styles
├── tests/                  # Automated tests
│   ├── conftest.py         # pytest fixtures
│   └── test_classifier.py  # Classification engine tests
├── .env                    # Environment variables (local secrets)
├── .env.example            # Example environment variables
├── requirements.txt        # Python dependencies
└── alembic.ini             # Alembic configuration
```

### Layer responsibilities

| Layer | Responsibility |
|-------|----------------|
| `routers/` | Receive HTTP requests, validate input, call services, return responses |
| `services/` | Contain business rules (classification, auth, PDF generation, AI) |
| `models.py` | Define database tables with SQLAlchemy |
| `schemas.py` | Define request/response shapes with Pydantic |
| `database.py` | Manage async database connections and sessions |
| `static/` | Serve the user-facing frontend |
| `tests/` | Verify that core logic works correctly |

---

## Technologies Used

### Backend

| Technology | Purpose |
|------------|---------|
| **Python 3.12+** | Primary programming language |
| **FastAPI 0.111.0** | Modern, high-performance web framework for building APIs |
| **Uvicorn 0.29.0** | ASGI server that runs the FastAPI application |
| **SQLAlchemy 2.0.30** | Object-Relational Mapper (ORM) for database interaction |
| **asyncpg 0.29.0** | Async PostgreSQL driver |
| **Alembic 1.13.1** | Database migration tool |
| **Pydantic 2.7.1** | Data validation and serialization |
| **python-jose** | JWT token creation and verification |
| **passlib** | Secure password hashing with bcrypt |

### External Services

| Technology | Purpose |
|------------|---------|
| **Google Generative AI (Gemini)** | Provides AI explanations of classifications and answers user follow-up questions |
| **PostgreSQL** | Relational database for users, shipments, and regulation updates |

### PDF & Document Generation

| Technology | Purpose |
|------------|---------|
| **ReportLab 4.2.0** | Generates IATA-style Shipper's Declaration PDFs |

### Frontend

| Technology | Purpose |
|------------|---------|
| **HTML5** | Page structure |
| **CSS3** | Styling, responsive layout, design system |
| **Vanilla JavaScript** | Interactivity, API calls, auth state management |

### Testing

| Technology | Purpose |
|------------|---------|
| **pytest 8.2.0** | Test runner |
| **pytest-asyncio 0.23.7** | Async test support |

### Planned / Stubbed

| Technology | Status |
|------------|--------|
| **Lemon Squeezy** | Subscription billing and pay-per-document credits |
| **APScheduler** | Scheduled monthly reset of document counters |
| **Stripe 9.9.0** | Listed in dependencies and environment example, but payment/subscription logic is not yet implemented |

---

## How the application works

### Authentication flow
1. User registers or logs in via the frontend (`index.html`).
2. The backend hashes/verifies the password and returns a JWT access token.
3. The frontend stores the token in `localStorage` and includes it in subsequent API requests.

### Classification flow
1. User submits battery details in `app.html`.
2. `POST /api/classify/` sanitizes input, validates it, and checks the user's monthly plan limit and pay-per-document credits.
3. `services/classifier.classify()` applies regulation rules to determine UN number, packing instruction, section, hazard class, and requirements.
4. The result is saved as a `Shipment` record, and either the monthly usage counter is incremented or a per-document credit is deducted.

### Billing flow
1. User selects a plan or pay-per-document credits in `app.html`.
2. `POST /api/billing/checkout/{plan}` creates a Lemon Squeezy checkout URL.
3. After successful payment, Lemon Squeezy sends a webhook to `POST /api/billing/webhook`.
4. The webhook updates the user's plan, subscription status, and credits in the database.
5. Users can view their billing status at `GET /api/billing/status` and cancel subscriptions at `POST /api/billing/cancel`.

### PDF generation flow
1. User clicks "Download Shipper's Declaration PDF" for a saved shipment.
2. `POST /api/documents/generate/{shipment_id}` verifies ownership.
3. `services.pdf_generator.generate_shippers_declaration()` builds a professional PDF with ReportLab.
4. The PDF is returned as a downloadable file.

### AI explanation flow
1. User clicks "Explain this in plain English" or submits a follow-up question.
2. `POST /api/classify/explain` sends classification details to Google Gemini.
3. Gemini returns a concise, practical explanation, or a fallback response if the service is unavailable or rate-limited.

---

## Environment Variables

The following variables are required or expected at runtime:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/batteryship
SECRET_KEY=your-secret-key-min-32-chars
GEMINI_API_KEY=your-gemini-api-key
ENVIRONMENT=development
STRIPE_SECRET_KEY=sk_test_your_stripe_key
LEMONSQUEEZY_API_KEY=your-lemonsqueezy-api-key
LEMONSQUEEZY_STORE_ID=your-store-id
LEMONSQUEEZY_WEBHOOK_SECRET=your-webhook-secret
LEMONSQUEEZY_VARIANT_STARTER=your-starter-variant-id
LEMONSQUEEZY_VARIANT_GROWTH=your-growth-variant-id
LEMONSQUEEZY_VARIANT_PERDOC=your-perdoc-variant-id
APP_URL=http://localhost:8000
```

---

## Running the project

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables (copy `.env.example` to `.env`).

3. Run database migrations:
   ```bash
   alembic upgrade head
   ```

4. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

5. Open `http://localhost:8000` in the browser.

---

## Testing

Run the test suite with:

```bash
pytest
```

The current tests focus on the classification engine in `services/classifier.py`.

---

## Notes & Future Improvements

- There is no `README.md` yet; this document can serve as the project overview.
- The `SECRET_KEY` currently has a fallback value for development and should be changed in production.
- Stripe is included as a dependency but not yet wired into the application.
- AI rate limiting is stored in memory, so it resets when the server restarts.
- The monthly document counter now resets automatically on the 1st of each month via APScheduler.

## Recent fixes

- **Database schema** — increased `shipments.packing_instruction` from `VARCHAR(20)` to `VARCHAR(100)` so long instructions like `"Refer to IATA DGR Special Provision A154"` can be stored. Applied via Alembic migration `2f7d639f6101`.
- **Static file 404s** — missing static files (e.g. `favicon.ico`) now return a clean `404` instead of an unhandled `500` error.
- **Gemini error handling** — quota/rate-limit errors from the Gemini API are logged server-side and no longer exposed to users. The UI receives a friendly fallback explanation instead.
