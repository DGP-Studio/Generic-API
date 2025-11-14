# Git Repository Management API

This module provides API endpoints to manage git repository information in the system.

## Features

The API allows you to:
- Store git repository information (name, URLs, type, token)
- Retrieve all registered git repositories
- Create new git repository records
- Update existing git repository records (by ID or name)
- Delete git repository records (by ID or name)

## Data Model

Each git repository record contains:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | Integer | Auto | Primary key (auto-generated) |
| `name` | String(255) | ✓ | Friendly name or internal identifier |
| `web_url` | String(512) | ✓ | Web page URL of the repository |
| `https_url` | String(512) | ✗ | HTTPS clone URL |
| `ssh_url` | String(512) | ✗ | SSH clone URL |
| `type` | String(50) | ✗ | Repository type (e.g., "public" or "private") |
| `token` | String(512) | ✗ | Access token |

## API Endpoints

All endpoints require API token authentication via the `Authorization: Bearer <token>` header.

### 1. Get All Repositories
```
GET /{region}/git-repository/all
```

Returns all git repositories in the database.

**Response Example:**
```json
{
  "retcode": 0,
  "message": "Successfully fetched all git repositories in region 'cn'",
  "data": [
    {
      "id": 1,
      "name": "snap-hutao",
      "region": "cn",
      "web_url": "https://github.com/DGP-Studio/Snap.Hutao",
      "https_url": "https://github.com/DGP-Studio/Snap.Hutao.git",
      "ssh_url": "git@github.com:DGP-Studio/Snap.Hutao.git",
      "type": "public",
      "token": null,
      "username": null
    }
  ]
}
```

### 2. Create Repository
```
POST /{region}/git-repository/create
```

Creates a new git repository record.

**Request Body:**
```json
{
  "name": "my-repo",
  "region": "cn",
  "web_url": "https://github.com/user/repo",
  "https_url": "https://github.com/user/repo.git",
  "ssh_url": "git@github.com:user/repo.git",
  "type": "public",
  "token": "ghp_xxxxxxxxxxxx",
  "username": "myuser"
}
```

**Response Example:**
```json
{
  "retcode": 0,
  "message": "Git repository created successfully",
  "data": {
    "id": 2,
    "name": "my-repo",
    "region": "cn",
    "web_url": "https://github.com/user/repo",
    "https_url": "https://github.com/user/repo.git",
    "ssh_url": "git@github.com:user/repo.git",
    "type": "public",
    "token": "ghp_xxxxxxxxxxxx",
    "username": "myuser"
  }
}
```

### 3. Update Repository
```
PUT /{region}/git-repository/update?repo_id={id}
```

Updates a git repository by ID. Only the fields provided in the request body will be updated.

**Query Parameters:**
- `repo_id` (required): Repository ID

**Request Body (partial update):**
```json
{
  "web_url": "https://github.com/user/new-repo",
  "type": "private"
}
```

**Response Example:**
```json
{
  "retcode": 0,
  "message": "Git repository updated successfully",
  "data": {
    "id": 2,
    "name": "my-repo",
    "region": "cn",
    "web_url": "https://github.com/user/new-repo",
    "https_url": "https://github.com/user/repo.git",
    "ssh_url": "git@github.com:user/repo.git",
    "type": "private",
    "token": "ghp_xxxxxxxxxxxx",
    "username": "myuser"
  }
}
```

### 4. Delete Repository
```
DELETE /{region}/git-repository/delete?repo_id={id}
```

Deletes a git repository by ID.

**Query Parameters:**
- `repo_id` (required): Repository ID

**Response Example:**
```json
{
  "retcode": 0,
  "message": "Git repository deleted successfully",
  "data": {
    "success": true
  }
}
```

## Database Setup

### Option 1: Using Python Initialization Script
```bash
python3 mysql_app/init_db.py
```

### Option 2: Using SQL Script
```bash
mysql -u <user> -p <database> < sql/create_git_repositories_table.sql
```

### Option 3: Auto-creation via SQLAlchemy
The table will be created automatically when the application starts if it doesn't exist (using SQLAlchemy's `create_all()` method).

## Testing

A test script is provided to validate all API endpoints:

```bash
# Set environment variables
export API_TOKEN=your_api_token_here

# Run the test
python3 test_git_repository.py
```

The test script will:
1. Create a test repository
2. Retrieve all repositories
3. Get repository by name
4. Create repository with duplicate name
5. Update the repository by ID
6. Delete the repositories
7. Verify deletion

## Region Support

The API is available on all three regions:
- `/cn/git-repository/*` - China region
- `/global/git-repository/*` - Global region
- `/fj/git-repository/*` - Fujian region

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message description"
}
```

Common error codes:
- `400` - Bad request (e.g., missing required parameters)
- `401` - Unauthorized (invalid or missing API token)
- `404` - Not found (repository doesn't exist)
- `500` - Internal server error

## Implementation Files

- `mysql_app/models.py` - SQLAlchemy model definition
- `mysql_app/schemas.py` - Pydantic schemas for validation
- `mysql_app/crud.py` - Database CRUD operations
- `routers/git_repository.py` - FastAPI router with endpoints
- `mysql_app/init_db.py` - Database initialization script
- `sql/create_git_repositories_table.sql` - SQL table creation script
- `test_git_repository.py` - Test script for API validation
