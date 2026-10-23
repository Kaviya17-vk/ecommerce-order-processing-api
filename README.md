
# E-Commerce Order Processing API

## Project Description

This project is a backend API for managing products, shopping carts,
orders, stock, payments, order history and sales reports.

## Technologies Used

- Python
- FastAPI
- Pydantic
- SQLAlchemy ORM
- SQLite
- Swagger / OpenAPI
- Git and GitHub

## Features

- Product CRUD operations
- Shopping cart management
- Order creation and total calculation
- Stock validation and stock restoration on cancellation
- Order status workflow validation
- Payment simulation
- Order history and search filters
- Sales reports

## Installation

1. Install Python.
2. Open the project folder in VS Code.
3. Create a virtual environment:

   `python -m venv venv`

4. Activate the environment in Windows PowerShell:

   `.\venv\Scripts\Activate.ps1`

5. Install the dependencies:

   `python -m pip install -r requirements.txt`

## Run the Application

`uvicorn main:app --reload`

## Swagger Documentation

Open the following URL in your browser:

`http://127.0.0.1:8000/docs`

## Database

SQLite is used as the default database.
The database tables are created automatically when the application starts.

## Order Processing Flow

Product Creation -> Add to Cart -> Create Order ->
Stock Reduction -> Payment -> Shipping -> Delivery

## Cancellation

Orders can be cancelled while Pending or Confirmed.
The purchased stock is restored when an order is cancelled.
