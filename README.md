# Trading Signal Webhook Backend

A backend service built with **Django** and **Django REST Framework** that receives trading signals via webhooks, executes them on a mock broker, and broadcasts real-time order status updates via WebSockets (**Django Channels**).

This project demonstrates a robust, production-ready architecture handling concurrency, security, and real-time data flow.

## 🚀 Features

- **Signal Parsing**: Validates incoming trading signals (regex-based) for BUY/SELL actions, SL/TP logic, and optional entry prices.
- **Order Lifecycle**: Simulates order execution (Pending → Executed → Closed) using background threads (no heavy Celery dependency needed for this demo).
- **Real-Time Updates**: Broadcasts order status changes to connected clients via WebSockets (`/ws/orders`).
- **Security**: 
  - API Key authentication for all endpoints.
  - **Fernet Encryption** for storing sensitive broker API keys at rest.
- **Audit Logging**: Tracks every signal received, order created, and account action.
- **REST API**: Clean, documented endpoints for managing accounts and orders.

## 🛠 Tech Stack

- **Python 3.11+**
- **Django 5.0** & **Django REST Framework**
- **Django Channels** & **Daphne** (ASGI)
- **PostgreSQL** (production-ready config) or SQLite (dev)
- **Fernet (Cryptography)** for encryption

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/emonhossennn/Trading-signals-via-webhook
   cd trading-signal-backend
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment:**
   Copy `.env.example` to `.env` and set your keys:
   ```bash
   cp .env.example .env
   ```
   *Note: For local dev, the default SQLite settings in `settings.py` work out of the box if you don't set DB vars.*

5. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Start the Server:**
   ```bash
   python manage.py runserver
   ```
   *Note: This runs via ASGI (Daphne) automatically to support WebSockets.*

## 🔌 API Usage

### 1. Create an Account & Link Broker
First, register a user and link a mock broker account.

**POST** `/accounts`
```json
{
  "username": "trader1",
  "broker_name": "MetaTrader 5",
  "account_id": "12345678",
  "api_key": "raw-broker-key-to-encrypt"
}
```
**Response:**
```json
{
  "api_key": "YOUR_GENERATED_API_KEY",  <-- SAVE THIS!
  "user": { ... }
}
```

### 2. Connect WebSocket (Real-Time Updates)
Connect a WebSocket client (like Postman or `wscat`) to listen for updates:
```
ws://localhost:8000/ws/orders/<your_user_id>
```

### 3. Send a Trading Signal (Webhook)
Simulate a signal coming from TradingView or a bot.

**POST** `/webhook/receive-signal`
**Headers:** `X-API-Key: YOUR_GENERATED_API_KEY`
**Body:**
```json
{
  "signal": "BUY EURUSD @1.0850\nSL 1.0820\nTP 1.0900"
}
```

**What happens next?**
1. Service validates the signal.
2. Creates an order with status `pending`.
3. **Simulates execution (5s later):** Updates status to `executed`.
4. **Simulates close (10s later):** Updates status to `closed`.
5. **Real-time notification:** You'll see JSON messages arriving on the WebSocket for each state change.

### 4. Check Analytics
**GET** `/analytics`
Returns total trades and breakdown by instrument.

## 🧪 Running Tests

Run the comprehensive test suite covering signal parsing, API endpoints, and WebSocket connectivity:

```bash
python manage.py test tests/ -v 2
```

## Project Structure
- `signals_app/signal_parser.py` — Core regex parsing logic
- `signals_app/order_manager.py` — Lifecycle simulation thread
- `signals_app/consumers.py` — WebSocket handler
- `signals_app/security.py` — Encryption utilities
