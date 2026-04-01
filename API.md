# API Reference

Base URL: `http://localhost:8000`

Timezones:
- If `start_time`/`end_time` are sent without a timezone offset, the backend assumes Asia/Kolkata (UTC+05:30).
- If you include an offset (e.g. `+05:30`), it is respected as-is.

Authentication:
- Admin routes require admin JWT in `Authorization: Bearer <token>`
- Client routes require client JWT in `Authorization: Bearer <token>`

Campaign ID rules:
- Campaign IDs are user-provided (no internal numeric ID generation)
- Allowed chars: letters, numbers, `_`, `-`
- Max length: 10

Storage file naming:
- Campaign metadata: `storage/campaigns/{campaign_id}/{campaign_id}.json`
- Timeseries data: `storage/campaigns/{campaign_id}/{campaign_id}.csv`

## Health

### GET /health

Response `200`:
```json
{
  "status": "healthy",
  "app": "VDS Campaign Dashboard"
}
```

## Authentication

### POST /api/auth/admin/login

Request:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

Response `200`:
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "role": "admin",
  "username": "admin",
  "display_name": "System Admin"
}
```

### POST /api/auth/client/login

Request:
```json
{
  "username": "client1",
  "password": "client123"
}
```

Response `200`:
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "role": "client",
  "username": "client1",
  "display_name": "Client One"
}
```

## Admin APIs

### POST /api/admin/campaign

Request:
```json
{
  "campaign_id": "CMP-001",
  "name": "Q2 Outreach",
  "start_time": "2026-03-31T10:00:00+00:00",
  "end_time": "2026-03-31T12:00:00+00:00",
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

Response `201`:
```json
{
  "id": "CMP-001",
  "name": "Q2 Outreach",
  "start_time": "2026-03-31T10:00:00Z",
  "end_time": "2026-03-31T12:00:00Z",
  "target_total": 1200,
  "status": "PLANNED",
  "config": {
    "id": "CMP-001",
    "campaign_id": "CMP-001",
    "connected_ratio": 0.62,
    "not_connected_ratio": 0.23,
    "pending_ratio": 0.15,
    "curve_type": "sigmoid",
    "noise_level": 0.02,
    "interval_seconds": 60
  }
}
```

### GET /api/admin/campaigns

Response `200`:
```json
[
  {
    "id": "CMP-001",
    "name": "Q2 Outreach",
    "start_time": "2026-03-31T10:00:00Z",
    "end_time": "2026-03-31T12:00:00Z",
    "target_total": 1200,
    "status": "READY",
    "config": {
      "id": "CMP-001",
      "campaign_id": "CMP-001",
      "connected_ratio": 0.62,
      "not_connected_ratio": 0.23,
      "pending_ratio": 0.15,
      "curve_type": "sigmoid",
      "noise_level": 0.02,
      "interval_seconds": 60
    }
  }
]
```

### GET /api/admin/campaign/{campaign_id}

Response `200`:
```json
{
  "id": "CMP-001",
  "name": "Q2 Outreach",
  "start_time": "2026-03-31T10:00:00Z",
  "end_time": "2026-03-31T12:00:00Z",
  "target_total": 1200,
  "status": "READY",
  "config": {
    "id": "CMP-001",
    "campaign_id": "CMP-001",
    "connected_ratio": 0.62,
    "not_connected_ratio": 0.23,
    "pending_ratio": 0.15,
    "curve_type": "sigmoid",
    "noise_level": 0.02,
    "interval_seconds": 60
  }
}
```

### PUT /api/admin/campaign/{campaign_id}

Request:
```json
{
  "name": "Q2 Outreach Updated",
  "start_time": "2026-03-31T10:30:00+00:00",
  "end_time": "2026-03-31T12:30:00+00:00",
  "target_total": 1500,
  "config": {
    "connected_ratio": 0.6,
    "not_connected_ratio": 0.25,
    "pending_ratio": 0.15,
    "curve_type": "sigmoid",
    "noise_level": 0.02,
    "interval_seconds": 60
  }
}
```

Response `200`:
```json
{
  "id": "CMP-001",
  "name": "Q2 Outreach Updated",
  "start_time": "2026-03-31T10:30:00Z",
  "end_time": "2026-03-31T12:30:00Z",
  "target_total": 1500,
  "status": "PLANNED",
  "config": {
    "id": "CMP-001",
    "campaign_id": "CMP-001",
    "connected_ratio": 0.6,
    "not_connected_ratio": 0.25,
    "pending_ratio": 0.15,
    "curve_type": "sigmoid",
    "noise_level": 0.02,
    "interval_seconds": 60
  }
}
```

### POST /api/admin/campaign/{campaign_id}/generate

Response `200`:
```json
{
  "message": "Simulation generated successfully for campaign CMP-001",
  "rows_written": 121
}
```

### POST /api/admin/campaign/{campaign_id}/timeseries/upload

Content type: `multipart/form-data`
- field name: `file`

CSV headers must be exactly:
`time,connected,notconnected`

Response `200`:
```json
{
  "message": "CSV uploaded successfully for campaign CMP-001",
  "rows_written": 200,
  "columns": ["time", "connected", "notconnected"]
}
```

### GET /api/admin/campaign/{campaign_id}/live

Response `200`:
```json
{
  "campaign_id": "CMP-001",
  "timestamp": "2026-03-31T11:00:00Z",
  "total_uploads": 700,
  "connected": 420,
  "not_connected": 280
}
```

### GET /api/admin/campaigns/live

Response `200`:
```json
[
  {
    "campaign_id": "CMP-001",
    "timestamp": "2026-03-31T11:00:00Z",
    "total_uploads": 700,
    "connected": 420,
    "not_connected": 280
  }
]
```

## Client APIs

### GET /api/client/campaigns

Response `200`:
```json
[
  {
    "id": "CMP-001",
    "name": "Q2 Outreach",
    "start_time": "2026-03-31T10:00:00Z",
    "end_time": "2026-03-31T12:00:00Z",
    "target_total": 1200,
    "status": "IN_PROGRESS",
    "config": {
      "id": "CMP-001",
      "campaign_id": "CMP-001",
      "connected_ratio": 0.62,
      "not_connected_ratio": 0.23,
      "pending_ratio": 0.15,
      "curve_type": "sigmoid",
      "noise_level": 0.02,
      "interval_seconds": 60
    }
  }
]
```

### GET /api/client/campaign/{campaign_id}

Response `200`:
```json
{
  "id": "CMP-001",
  "name": "Q2 Outreach",
  "start_time": "2026-03-31T10:00:00Z",
  "end_time": "2026-03-31T12:00:00Z",
  "target_total": 1200,
  "status": "IN_PROGRESS",
  "config": {
    "id": "CMP-001",
    "campaign_id": "CMP-001",
    "connected_ratio": 0.62,
    "not_connected_ratio": 0.23,
    "pending_ratio": 0.15,
    "curve_type": "sigmoid",
    "noise_level": 0.02,
    "interval_seconds": 60
  }
}
```

### GET /api/client/campaign/{campaign_id}/live

Response `200`:
```json
{
  "campaign_id": "CMP-001",
  "timestamp": "2026-03-31T11:00:00Z",
  "total_uploads": 700,
  "connected": 420,
  "not_connected": 280
}
```

### GET /api/client/campaigns/live

Response `200`:
```json
[
  {
    "campaign_id": "CMP-001",
    "timestamp": "2026-03-31T11:00:00Z",
    "total_uploads": 700,
    "connected": 420,
    "not_connected": 280
  }
]
```

## Common Error Response

Response `4xx/5xx`:
```json
{
  "detail": "Error message"
}
```
