# Frontend Integration Guide - VDS Campaign Dashboard

Base URL: `http://localhost:8000`

Timezones:
- If `start_time`/`end_time` are sent without a timezone offset, the backend assumes Asia/Kolkata (UTC+05:30).
- If you include an offset (e.g. `+05:30`), it is respected as-is.

This backend now uses file storage only:
- Admin credentials: `storage/admin.json`
- Client credentials: `storage/clients.json`
- Campaign folders: `storage/campaigns/{campaign_id}`
- Campaign metadata JSON: `storage/campaigns/{campaign_id}/{campaign_id}.json`
- Timeseries CSV: `storage/campaigns/{campaign_id}/{campaign_id}.csv`

Campaign ID rules:
- campaign_id is required in create API
- max length is 10
- allowed chars: letters, numbers, `_`, `-`

Timeseries CSV format is fixed:
- Headers: `time,connected,notconnected`
- `time` format: `YYYY-MM-DD HH:MM:SS`

## 1. Authentication

### 1.1 Admin Login

`POST /api/auth/admin/login`

Request:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

Response:
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "role": "admin",
  "username": "admin",
  "display_name": "System Admin"
}
```

### 1.2 Client Login

`POST /api/auth/client/login`

Request:
```json
{
  "username": "client1",
  "password": "client123"
}
```

Response:
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "role": "client",
  "username": "client1",
  "display_name": "Client One"
}
```

## 2. Admin API (requires admin token)

Use header:
`Authorization: Bearer <admin_jwt>`

### 2.1 Create Campaign

`POST /api/admin/campaign`

```json
{
  "campaign_id": "CMP-001",
  "name": "Q2 Outreach",
  "start_time": "2026-03-30T08:00:00+00:00",
  "end_time": "2026-03-30T10:00:00+00:00",
  "target_total": 1200,
  "config": {
    "connected_ratio": 0.62,
    "not_connected_ratio": 0.23,
    "pending_ratio": 0.15,
    "curve_type": "sigmoid",
    "noise_level": 0.02,
    "interval_seconds": 60
  }
}
```

### 2.2 List Campaigns

`GET /api/admin/campaigns`

### 2.3 Get Campaign

`GET /api/admin/campaign/{id}`

### 2.4 Update Campaign

`PUT /api/admin/campaign/{id}`

Uses same body schema as create.

### 2.5 Generate Testing Timeseries CSV

`POST /api/admin/campaign/{id}/generate`

This creates `{campaign_id}.csv` automatically with required columns.

### 2.6 Upload Timeseries CSV

`POST /api/admin/campaign/{id}/timeseries/upload`

`multipart/form-data` with file field name: `file`

Validation rules:
- Headers must be exactly `time,connected,notconnected`
- `time` must be `YYYY-MM-DD HH:MM:SS`
- connected and notconnected must be integers >= 0

### 2.7 Live Stats (Admin)

`GET /api/admin/campaign/{id}/live`

Response shape:
```json
{
  "campaign_id": "CMP-001",
  "timestamp": "2026-03-30T09:15:00+00:00",
  "total_uploads": 748,
  "connected": 464,
  "not_connected": 284
}
```

### 2.8 Live Stats (All Campaigns)

`GET /api/admin/campaigns/live`

Response shape:
```json
[
  {
    "campaign_id": "CMP-001",
    "timestamp": "2026-03-30T09:15:00+00:00",
    "total_uploads": 748,
    "connected": 464,
    "not_connected": 284
  }
]
```

## 3. Client API (requires client token)

Use header:
`Authorization: Bearer <client_jwt>`

### 3.1 List Campaigns

`GET /api/client/campaigns`

### 3.2 Get Campaign

`GET /api/client/campaign/{id}`

### 3.3 Live Stats

`GET /api/client/campaign/{id}/live`

Response shape:
```json
{
  "campaign_id": "CMP-001",
  "timestamp": "2026-03-30T09:15:00+00:00",
  "total_uploads": 748,
  "connected": 464,
  "not_connected": 284
}
```

### 3.4 Live Stats (All Campaigns)

`GET /api/client/campaigns/live`

Response shape:
```json
[
  {
    "campaign_id": "CMP-001",
    "timestamp": "2026-03-30T09:15:00+00:00",
    "total_uploads": 748,
    "connected": 464,
    "not_connected": 284
  }
]
```

## 4. Health Check

`GET /health`

Response:
```json
{
  "status": "healthy",
  "app": "VDS Campaign Dashboard"
}
```

## 5. Default Testing Credentials

From seeded storage files:
- Admin: `admin` / `admin123`
- Client: `client1` / `client123`
- Client: `client2` / `client456`

You can change/add credentials manually in:
- `storage/admin.json`
- `storage/clients.json`
