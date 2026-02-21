# Trading Signal Webhook Backend

A backend service built with **Django** and **Django REST Framework** that receives trading signals via webhooks, executes them on a mock broker, and broadcasts real-time order status updates via WebSockets (**Django Channels**).

This project demonstrates a robust, production-ready architecture handling concurrency, security, and real-time data flow.

## Features

- **Signal Parsing**: Validates incoming trading signals (regex-based) for BUY/SELL actions, SL/TP logic, and optional entry prices.
- **Order Lifecycle**: Simulates order execution (Pending → Executed → Closed) using background threads (no heavy Celery dependency needed for this demo).
- **Real-Time Updates**: Broadcasts order status changes to connected clients via WebSockets (`/ws/orders`).
- **Security**: 
  - API Key authentication for all endpoints.
  - **Fernet Encryption** for storing sensitive broker API keys at rest.
- **Audit Logging**: Tracks every signal received, order created, and account action.
- **REST API**: Clean, documented endpoints for managing accounts and orders.

## Tech Stack

- **Python 3.11+**
- **Django 5.0** & **Django REST Framework**
- **Django Channels** & **Daphne** (ASGI)
- **PostgreSQL** (production-ready config) or SQLite (dev)
- **Fernet (Cryptography)** for encryption

## Installation

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

## API Usage Guide

1.  **Generate your API Key**: First, register your broker account (see API section below). You will receive an `api_key`. **Save this key immediately**, as it is hashed and cannot be recovered.
2. **Webhook URL**: Your webhook endpoint will be: `http://localhost:8000/webhook/receive-signal/`
3. **Authentication**: You must include the header `X-API-Key: <your_generated_key>` in every POST request.
4. **Payload Format**: The service expects a JSON body with a `signal` field containing raw text. Example:
    ```json
    { "signal": "BUY EURUSD @1.10 SL 1.09 TP 1.12" }
    ```

### 1. Register a Broker Account
**POST** `/accounts/`
Register your user and securely store your broker credentials.
- **Request Body**:
  ```json
  {
    "username": "my_user",
    "broker_name": "MetaTrader 5",
    "account_id": "88776655",
    "api_key": "YOUR_BROKER_SECRET"
  }
  ```
- **Response**: Returns your specific system `api_key` and your `user_id`. Use these for all further interactions.

### 2. Receive Trading Signals (Webhook)
**POST** `/webhook/receive-signal/`
- **Header**: `X-API-Key: <your_key>`
- **Body**: `{ "signal": "BUY BTCUSD SL 60000 TP 70000" }`

### 3. List Orders
**GET** `/orders/`
- **Header**: `X-API-Key: <your_key>`
- Returns a list of all orders associated with your account and their current status.

### 4. Get Order Detail
**GET** `/orders/<order_id>/`
- **Header**: `X-API-Key: <your_key>`
- Returns details for a specific order.

### 5. Real-time Statuses (WebSocket)
To get live updates on order execution without polling, connect to:
`ws://localhost:8000/ws/orders/<user_id>`

## Running Tests

Run the comprehensive test suite covering signal parsing, API endpoints, and WebSocket connectivity:

```bash
python manage.py test tests/ -v 2
```

## Internal Project Structure
- `signals_app/signal_parser.py`: Regex logic for parsing various signal formats.
- `signals_app/order_manager.py`: Handles background simulation of order lifecycles (Pending -> Executed -> Closed).
- `signals_app/consumers.py`: Real-time WebSocket communication logic.
- `signals_app/security.py`: Encryption (Fernet) wrapper for protecting sensitive broker keys.
- `tests/`: Pytest suite for automated logic verification.
