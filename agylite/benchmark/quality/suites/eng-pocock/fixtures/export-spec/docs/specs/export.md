# Spec: CSV export of orders

## Problem Statement
Shop owners copy orders into spreadsheets by hand to do their accounts.

## Solution
An "Export CSV" button on the orders page downloads the orders that match the current filters.

## User Stories
1. As a shop owner, I want to download my orders as CSV, so that I can do my accounts in a spreadsheet.
2. As a shop owner, I want the export to respect the date and status filters, so that I get only the orders I need.
3. As a shop owner, I want amounts in the shop's currency with two decimals, so that totals add up in the spreadsheet.
4. As a shop owner with 50,000 orders, I want the export to stream, so that the download starts at once.

## Implementation Decisions
- A new database view `orders_export` joins orders, customers and line totals.
- A new endpoint `GET /orders/export.csv` accepts the same filter parameters as `GET /orders` and streams rows.
- The orders page gets an "Export CSV" button that links to the endpoint with the current filters.
- Columns: order number, date (ISO 8601), customer name, status, total, currency.

## Testing Decisions
- Test through the HTTP endpoint with seeded orders; assert the CSV body.

## Out of Scope
Excel format, scheduled exports, exporting line items.
