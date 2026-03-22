# Mobile Dealer SaaS API — Documentation

## 🏗️ Architectural Overview

The **Mobile Dealer SaaS** platform uses a multi-layered approach to ensure scalability, security, and data partitioning for different tenants (Stores).

### 🔐 Authentication System

- **Email-based Auth**: `CustomUser` model uses email as the primary login.
- **JWT (JSON Web Token)**: State-free authentication via `djangorestframework-simplejwt`.
- **User Roles**: 
  - `SuperUser`: Global access to all stores, users, and system stats.
  - `StoreOwner`: Ownership over their stores, products, and sales.
  - `StoreKeeper`: Read-only/write-limited access as a sub-account of a store.

### 🏠 Multi-Tenancy

- Every **Store** is owned by a `StoreOwner`.
- **Products**, **Sales**, and **Allocations** are strictly filtered by the owner's store in the ViewSets.
- Data integrity is enforced via **ForeignKey** relationships to the `Store` model.

### 📱 Specialized IMEI Logic

- **Validation**: All IMEI strings must satisfy the **Luhn Checksum** (15 digits).
- **Utility**: `inventory/utils.py` contains `validate_imei` and a placeholder for 3rd-party spec lookups.
- **Product Status**: Tracking device lifecycle: `Available` → `Allocated` → `Sold`.

### 💵 Sales & Automatic Lifecycle

- Creating a **Sale** triggers an atomic update on the associated product to `Sold`.
- **Sales Report**: Exportable CSV functionality for owners to track revenue and performance.

### 📅 Subscription Enforcement

- **Decorator Logic**: `check_subscription` (in `stores/decorators.py`) can be applied to actions (like adding staff) to enforce plan-based limits.
- **Plan Limits**: Staff allocations and store counts are managed via `Subscription` models attached to stores.

### 🖼️ Cloudinary Storage

- **Automated Media**: All `profile_picture`, `logo`, and `product.image` fields use `CloudinaryField`.
- **Efficiency**: Images are stored externally, optimized for delivery over CDNs.

## 🛠️ Key Endpoints & Parameters

### Inventory Filter Parameters
Use the following query parameters at `/api/inventory/` and `/api/marketplace/`:
- `brand`: Search brands (case-insensitive)
- `model`: Search models (case-insensitive)
- `status`: One of `Available`, `Allocated`, `Sold`
- `min_price`: Minimum selling price
- `max_price`: Maximum selling price

### Bulk Sold Endpoint
`POST /api/inventory/bulk-sold/`
**Body**:
```json
{
  "ids": [1, 2, 3],
  "imeis": ["3579..."]
}
```

### Marketplace (Public)
`GET /api/marketplace/`
Returns only **Available** products from **Active** stores. No authentication required.

## 🚢 Deployment Roadmap

1. **Environment Variables**: Set `CLOUDINARY_*` and `SECRET_KEY`.
2. **Database Migration**: Switch to **PostgreSQL** in `core/settings.py` for high concurrency.
3. **CORS Policies**: Restrict `CORS_ALLOW_ALL_ORIGINS = True` to specific frontend domains.
4. **Media CDN**: Ensure Cloudinary API responsiveness matches traffic targets.
