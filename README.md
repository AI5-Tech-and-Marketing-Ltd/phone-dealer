# Mobile Dealer SaaS REST API

A robust, production-ready REST API for a **Mobile Dealer SaaS** platform built with **Django 5.x** and **Django Rest Framework (DRF)**.

## 🚀 Features

- **Multi-Tenancy**: Dedicated store management partitioned per owner.
- **RBAC (Role-Based Access Control)**: Permissions for SuperUsers, StoreOwners, and StoreKeepers.
- **IMEI-Based Inventory**: Specialized device tracking with Luhn checksum validation.
- **SaaS Subscription Logic**: Plans, staff limits, and expiry dates enforcement.
- **Sales & Reports**: Mark products as sold with automatic status updates and CSV export.
- **Cloudinary Integration**: Automatic media storage for profile pictures, logos, and product images.
- **Interactive Documentation**: Swagger/OpenAPI 3.0 at `/api/docs/`.

## 🛠️ Technical Stack

- **Framework**: Django 5.x, DRF
- **Authentication**: JWT (SimpleJWT)
- **Database**: SQLite (Dev), PostgreSQL (Production-ready)
- **Documentation**: drf-spectacular
- **Storage**: Cloudinary

## 🛠️ Installation & Setup

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

4. **Set Environment Variables**:
   Create a `.env` file or export the following:
   ```bash
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret
   ```

5. **Run Migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Start the server**:
   ```bash
   python manage.py runserver
   ```

## 📖 API Documentation

- **Swagger UI**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **Redoc**: [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)
- **Raw Schema**: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)

## 📂 Project Structure

- `accounts/`: User models, JWT-based auth, and profiles.
- `stores/`: Store multi-tenancy and subscription management.
- `inventory/`: IMEI-based product tracking and public marketplace.
- `sales/`: Revenue recording and reporting.
- `admin_portal/`: System-wide analytics dashboard for SuperAdmins.
