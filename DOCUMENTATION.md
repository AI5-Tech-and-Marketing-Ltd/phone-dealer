# 📱 Mobile Dealer SaaS API & Frontend Implementation Guide

## 🏗️ System Architecture
The platform is designed as a **Multi-tenant SaaS** for mobile phone dealers. It partitions data by **Store**, uses **RBAC** for permissions, and manages a global **TAC (Type Allocation Code)** database for device lookup and specifications.

---

## 🔐 Roles & Permissions
- **SuperUser**: Global system access. Can manage all users, stores, billing, and view cross-tenant analytics.
- **StoreOwner**: Primary tenant account. Has full control over their stores, inventory, subscriptions, and sub-accounts.
- **StoreKeeper**: Staff/Employee account linked to a specific store. Can manage products and allocations within the store they are assigned to.

---

## 📦 Core Modules & Endpoints

### 1. Authentication (`/api/auth/`)
- `POST api/auth/signup/`: Public registration for new **StoreOwners**.
- `POST api/auth/login/`: Returns JWT tokens (Access & Refresh tokens).
- `POST api/auth/resend-activation/`: Resend account verification email.
- `POST api/auth/password-reset/`: Initiate "Forgot Password" flow via email.
- `POST api/auth/logout/`: Blacklists the refresh token.

### 2. Store & Subscription Management (`/api/stores/`)
- `GET api/stores/`: List and manage stores owned by the current user.
- `GET api/stores/plans/`: List available subscription tiers (includes Title, Price per user, Features, and Billing Cycle).
- `POST api/stores/subscribe/`: Initiate a new subscription. Requires `plan_id` and `staff_count`. Calculates total price dynamically (`plan.price * staff_count`).
- `GET api/stores/staff/`: Full CRUD for users linked to the owner's store.
- `GET api/stores/bills/`: View invoices, payment status, and Paystack references.
- `POST api/stores/bills/{id}/pay/`: Returns a secure Paystack checkout URL for pending payments.

### 3. Inventory & Device Intelligence (`/api/inventory/`)
- `GET api/inventory/tac-list/`: Paginated explorer for the global TAC database (22,000+ records). Supports `page` and `page_size` (max 200).
- `GET api/inventory/imei-lookup/{imei}/`: Advanced device lookup. Returns specs (Brand, Model, AKA names) from the TAC database and checks if the device exists in your store.
- `POST api/inventory/conditions/`: Manage custom status labels per store (e.g., "Mint", "Fair", "Cracked Screen").
- `POST api/inventory/bulk-sold/`: Bulk update product status to "Sold" using IDs or IMEI lists.
- `GET api/inventory/allocations/`: Track internal hand-offs of devices between staff members.

### 4. Admin Portal (`/api/admin-portal/`) — **SUPERUSER ONLY**
- `POST api/admin-portal/users/assign-store/`: Link any user to any store and set their role (Owner vs Keeper).
- `POST api/admin-portal/stores/{id}/change-owner/`: Atomically transfer primary ownership of a store.
- `GET api/admin-portal/dashboard-stats/`: System-wide KPI tracking (Total users, active stores, global inventory volume).

---

## 🎨 Frontend Implementation Guide

### 🔑 Authentication Flow
1.  **Security**: Store the `access` token in memory/state and the `refresh` token in a secure cookie or encrypted storage.
2.  **Interceptor**: Attach `Authorization: Bearer <token>` to all private API calls. Automatically call `token/refresh` if a 401 error is received.
3.  **Dynamic UI**: Use the `role` from the user profile to toggle visibility of administrative menus.

### 🛒 Subscription Logic
1.  **Tier Selection**: Fetch available plans from `api/stores/plans/`.
2.  **Staff Selection**: Allow the user to pick the number of seats. Total price updates in real-time as `Plan.price_per_user * Staff_Count`.
3.  **Payment Processing**: On subscription initiation, redirect the user to the provided `checkout_url`.
4.  **Verification**: After payment, the user is redirected back. The backend verifies via **Paystack Webhooks** and **Callbacks**.

### 📱 IMEI & Inventory UX
1.  **Rapid Entry**: Implement a 1D barcode scanner using the camera.
2.  **Intel Lookup**: Immediately call `api/inventory/imei-lookup/{imei}/`.
3.  **Smart Fill**: Auto-populate the `Brand` and `Model` input fields using the API response. This prevents data entry errors.
4.  **Conditions**: Fetch store-specific conditions from `api/inventory/conditions/` for the status dropdown.

### 🏘️ Multi-Tenancy Management
1.  **Store Context**: For users with multiple stores, include a "Store Switcher" that updates the application context.
2.  **Staff Invitation**: StoreOwners should use the `api/stores/staff/` endpoint to create accounts instead of a public signup link to ensure correct store linkage.

---

## 🔗 Model Relationships (ERD)
- **User** (Many-to-One) → **Store**: Staff are children of a store.
- **Store** (One-to-Many) → **Products**: Inventory belongs to a specific store.
- **Store** (One-to-Many) → **Subscriptions**: Stores maintain a history of plans.
- **Subscription** (Many-to-One) → **Plan**: Subscriptions derive pricing and features from a Plan record.
- **Bill** (One-to-One) → **Subscription**: Bills link financial transactions to service access.
- **Product** (Many-to-Many) → **Conditions**: Many products can share the same condition label defined by the store.

---

## 🛠️ Performance & Scalability Tips
- **Infinite Scroll**: For the `TAC-List`, use infinite scrolling. Loading 200 rows at a time provides a smooth UX for 22k records.
- **Cloudinary Optimization**: Use Cloudinary delivery URLs for images. Append transformation parameters (e.g., `q_auto,f_auto,w_500`) to significantly reduce page load time.
- **Atomic Operations**: Always use the `bulk-sold` endpoint for large inventory updates to ensure database consistency.

---

## 🚀 Deployment Checklist
- [ ] Set `DEBUG=False` and `PRODUCTION=True` in environment variables.
- [ ] Configure `ZEPTOMAIL_API_KEY` for transactional email delivery.
- [ ] Set `CLOUDINARY_URL` for secure media storage.
- [ ] Map Paystack Webhook to `/api/stores/payments/webhook/`.
- [ ] Configure `FRONTEND_URL` so reset links point to your client application.
