# TAC Database — Implementation & User Guide

This update migrates the Type Allocation Code (TAC) database from a flat CSV file (`tacdb.csv`) into a managed Django database table (`TacRecord`). This allows for dynamic updates, manual entries, and bulk management via the API and Admin Portal.

---

## 🚀 Key Features

1.  **Database Storage**: All TAC records are now stored in the database, allowing for O(1) lookups during IMEI validation.
2.  **Manual Entry**: SuperAdmins can now add individual TAC records via the API or Django Admin.
3.  **Bulk JSON Import**: Support for importing multiple records at once via a single JSON payload.
4.  **File Upload**: Support for seeding/updating the database by uploading CSV or Excel (`.xlsx`) files.
5.  **Dynamic Search**: A new search endpoint allows authenticated users to find device details by TAC, brand, or model name.

---

## 🛠️ Technical Implementation

### 1. New Model: `TacRecord`
- **Fields**: `tac` (8-digit unique ID), `brand`, `name`, `aka` (JSON array), `contributor`, `comment`, `gsmarena_1`, `gsmarena_2`.
- **Optimization**: `tac` is indexed for fast lookups.

### 2. API Endpoints (Base: `/inventory/tac/`)

| Method | Endpoint | Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/inventory/tac/` | SuperUser | Paginated list of all records. |
| `GET` | `/inventory/tac/search/?q=...` | Authenticated | Search by TAC, brand, or name (returns max 50). |
| `POST` | `/inventory/tac/create/` | SuperUser | Create a single record. |
| `POST` | `/inventory/tac/bulk/` | SuperUser | Bulk create/update via JSON. |
| `POST` | `/inventory/tac/upload/` | SuperUser | Upload CSV/Excel file. |

### 3. Management Command
A new command `seed_tac` is available to populate the database from the legacy CSV file:
```bash
python manage.py seed_tac --batch-size 1000
```

---

## 📖 How to Manage TAC Records

### Adding a Single Record (Manual)
**Endpoint**: `POST /inventory/tac/create/`
**Body**:
```json
{
  "tac": "35123456",
  "brand": "Apple",
  "name": "iPhone 13",
  "aka": ["A2633", "Global"]
}
```

### Bulk Uploading via File
1.  Prepare a CSV or Excel file.
2.  Ensure columns are in this order: `tac, brand, name, contributor, comment, gsmarena_1, gsmarena_2, aka`.
3.  Upload the file via `POST /inventory/tac/upload/` (using Multipart form-data).

### Searching for Devices
Users can search for device information without knowing the full IMEI:
**Endpoint**: `GET /inventory/tac/search/?q=iphone`

---

## ⚠️ Important Notes
- **Luhn Check**: IMEI lookups still perform a Luhn validation before querying the TAC database.
- **Legacy Fallback**: The `fetch_imei_info` utility will still check the `tacdb.csv` file if a TAC is not found in the database, ensuring zero downtime during the migration phase.
- **Pagination**: The list endpoint uses standard Django Rest Framework pagination (50 items per page by default).

---

## 📦 Dependencies Added
- `openpyxl`: Required for processing Excel (`.xlsx`) uploads.
