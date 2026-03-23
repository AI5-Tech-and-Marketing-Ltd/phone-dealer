# 📱 Mobile Dealer SaaS REST API

A robust, production-ready REST API for a **Mobile Dealer SaaS** platform built with **Django 5.x** and **Django Rest Framework (DRF)**. Designed for multi-tenant mobile device inventory, specify-lookup, and tiered subscription management.

## 🚀 Core Features

- **Multi-Tenancy Architecture**: Secure data partitioning based on the **Store** model. Owners manage their own sub-accounts, staff assignments, and inventory.
- **Advanced RBAC**: Integrated permissions for **SuperUsers**, **StoreOwners**, and **StoreKeepers**.
- **Device Intelligence**: 
    - **IMEI Lookup**: Automatic brand, model name, and AKA lookup using a global **TAC (Type Allocation Code)** database with 22,000+ records.
    - **Luhn Checksum**: Enforced validation on all device IMEIs to ensure data integrity.
    - **Custom Conditions**: Store-specific inventory status labels (e.g., "Cracked Screen", "Ex-UK", "Mint").
- **Tiered SaaS Billing**: 
    - **Model-Driven Plans**: Define complex subscription tiers with different features and pricing cycles.
    - **Per-User Pricing**: Scalable subscription model where costs are calculated based on the number of staff slots (`Plan Price * Slot Quantity`).
    - **Payment Integration**: Secure billing initiation with **Paystack** checkout redirects and webhook callbacks.
- **Transactional Communication**: Integrated **ZeptoMail** API for account activation emails and secure password recovery.
- **Cloudinary Integration**: Fully automated media management for store logos, profile pictures, and product imagery with CDN optimization.
- **Interactive API Schema**: Full OpenAPI 3.0 documentation via **Swagger UI** and **Redoc**.

## 🛠️ Technical Stack

- **Framework**: Django 5.x, Django Rest Framework (DRF)
- **Authentication**: JWT (SimpleJWT) with refresh token blacklisting
- **Mailing**: ZeptoMail SDK integration
- **Media Storage**: Cloudinary (external CDN storage)
- **Payment Processing**: Paystack (via secure bill reference system)
- **Documentation**: drf-spectacular

## 🛠️ Installation & Rapid Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd Phone_dealer
   ```

2. **Setup virtual environment**:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**:
   Create a `.env` file with the following keys:
   ```bash
   SECRET_KEY=your_django_secret
   DEBUG=True # Falsy on production
   ZEPTOMAIL_API_KEY=your_zeptomail_key
   CLOUDINARY_CLOUD_NAME=your_cloudinary_name
   CLOUDINARY_API_KEY=your_cloudinary_key
   CLOUDINARY_API_SECRET=your_cloudinary_secret
   PAYSTACK_SECRET_KEY=your_paystack_secret
   ```

5. **Run Migrations & TAC Setup**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create Admin User (Universal)**:
   ```bash
   python manage.py setup_admin
   ```

7. **Start Server**:
   ```bash
   python manage.py runserver
   ```

## 📖 API Reference Documentation

Access the following interactive docs locally at:
- **Swagger UI**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **Redoc**: [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)
- **Architecture Guide**: See [DOCUMENTATION.md](./DOCUMENTATION.md) for a deep dive into frontend implementation and data relations.

## 📂 Project Organization

- `accounts/`: Identity management, profile handling, and authentication flows.
- `stores/`: Tiered plans, multi-tenant billing, and store owner controls.
- `inventory/`: Global TAC database, device condition management, and stock movement.
- `admin_portal/`: System analytics and global administrative tools for SuperAdmins.
