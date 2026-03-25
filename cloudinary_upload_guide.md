# 🖼️ Frontend Cloudinary Upload Guide

This guide explains how to handle image uploads for **Store Banners (Cover Pictures)**, **Store Logos**, and **Product Images** using Cloudinary.

---

## 🚀 Recommended Method: Direct Upload (Unsigned)

Direct uploading to Cloudinary from the frontend is preferred. It reduces load on the Django backend and provides a faster user experience.

### 1. Cloudinary Setup
Use these details to configure your upload client (e.g., Axios or Cloudinary SDK):
- **Cloud Name**: `dslhc1058`
- **Store Preset**: `shop-banners` (Defined in `.env`)
- **Product Preset**: `product-images` (Defined in `.env`)

### 2. Implementation Example (React/JS)

```javascript
const uploadImage = async (file, type) => {
  const preset = type === 'product' ? 'product_preset_unsigned' : 'shop_preset_unsigned';
  const url = `https://api.cloudinary.com/v1_1/YOUR_CLOUD_NAME/image/upload`;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('upload_preset', preset);

  const response = await fetch(url, { method: 'POST', body: formData });
  const data = await response.json();

  return data.public_id; // Send this ID to the backend
};
```

### 3. Updating the Backend
Once you have the `public_id`, send it to the respective API endpoint.

| Feature | Model | Field | Endpoint |
| :--- | :--- | :--- | :--- |
| **Store Logo** | Store | `logo` | `PATCH /api/stores/{id}/` |
| **Store Banner** | Store | `cover_picture` | `PATCH /api/stores/{id}/` |
| **Product Image** | Product | `image` | `POST /api/inventory/` (or `PATCH`) |

## 🛠️ Recommended Method: Multipart Upload (Standard Django)

Since the backend now uses standard Django `ImageField` with `django-cloudinary-storage`, you can send files using standard `multipart/form-data` requests.

### Implementation Example (React/JS)

```javascript
const uploadToBackend = async (file, type, id) => {
  const formData = new FormData();
  const fieldName = type === 'product' ? 'image' : (type === 'logo' ? 'logo' : 'cover_picture');
  formData.append(fieldName, file);

  const url = type === 'product' ? `/api/inventory/${id}/` : `/api/stores/${id}/`;
  
  const response = await axios.patch(url, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};
```

---

## ⚡ Direct Upload to Cloudinary (Advanced)

You can still upload directly to Cloudinary if preferred, then send the `public_id` or `URL` to the backend. The backend will treat it as a file path.

---

## 💡 Frontend Tips

1. **Optimization**: Append Cloudinary transformation parameters to the retrieved URLs for performance:
   - Example: `https://res.cloudinary.com/demo/image/upload/w_500,c_fill,q_auto,f_auto/v1/sample.jpg`
2. **Preview**: Generate a local `URL.createObjectURL(file)` before uploading to show an instant preview to the user.
3. **Naming**: The presets are configured to append a unique suffix to filenames to avoid collisions.
