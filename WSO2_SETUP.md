# WSO2 APIM + Identity Server Setup Guide

End-to-end guide for running the microservice demo with WSO2 API Manager 4.3.0 and WSO2 Identity Server 7.0.0, including GitHub OAuth login.

## Architecture

```
Browser
  │
  ├── https://localhost:9443  ──► WSO2 Identity Server 7.0.0
  │                                  - User identity & OAuth2 token issuer
  │                                  - GitHub OAuth login
  │                                  - JWKS endpoint
  │
  ├── https://localhost:9444  ──► WSO2 API Manager 4.3.0
  │       (Publisher / DevPortal)     - API lifecycle management
  │                                  - Delegates auth to WSO2 IS (Key Manager)
  │
  ├── http://localhost:8281   ──► APIM Gateway (HTTP)
  └── https://localhost:8244  ──► APIM Gateway (HTTPS)
                                     │
                     ┌───────────────┼───────────────┐
                     ▼               ▼               ▼
              auth-service    product-service   order-service
              (port 8001)      (port 8002)      (port 8003)
                     │               │               │
                  auth-db       product-db       order-db
```

**Token flow:** Browser → APIM DevPortal → WSO2 IS (GitHub OAuth) → token issued by IS → APIM validates via IS JWKS → microservices validate `X-JWT-Assertion` header.

---

## Prerequisites

- Docker and Docker Compose
- A GitHub account for OAuth App creation

---

## Port Reference

| Service | Port | URL |
|---------|------|-----|
| WSO2 IS Console | 9443 | `https://localhost:9443/console` |
| WSO2 IS My Account | 9443 | `https://localhost:9443/myaccount` |
| APIM Publisher | 9444 | `https://localhost:9444/publisher` |
| APIM DevPortal | 9444 | `https://localhost:9444/devportal` |
| APIM Admin | 9444 | `https://localhost:9444/admin` |
| API Gateway HTTP | 8281 | `http://localhost:8281/` |
| API Gateway HTTPS | 8244 | `https://localhost:8244/` |

Default credentials for both IS and APIM: `admin` / `admin`

---

## Step 1 — Start Services

```bash
docker compose up -d
```

Startup order (automatic via `depends_on`):
1. Databases (postgres) — ~5 seconds
2. WSO2 IS — ~2 minutes
3. WSO2 APIM — ~3 minutes (waits for IS to be healthy)
4. Microservices — start after APIM is healthy

Check status:

```bash
docker compose ps
```

All services should show `healthy` or `Up`.

---

## Step 2 — Configure WSO2 IS as Key Manager in APIM

> Do this once. Config persists in the `wso2-apim-db` Docker volume.

1. Go to `https://localhost:9444/admin` → log in with `admin` / `admin`
2. **Settings → Key Managers → Add Key Manager**
3. Fill in the top fields:

| Field | Value |
|-------|-------|
| Name | `WSO2IS` |
| Key Manager Type | `WSO2 Identity Server` |
| Well-known URL | `https://wso2-is:9443/oauth2/oidcdiscovery/.well-known/openid-configuration` |

4. Click **Import** — endpoints auto-fill
5. Manually update every endpoint to use the values below (overwrite whatever was imported):

| Field | Value |
|-------|-------|
| Token Endpoint | `https://wso2-is:9443/oauth2/token` |
| Revoke Endpoint | `https://wso2-is:9443/oauth2/revoke` |
| Introspection Endpoint | `https://wso2-is:9443/oauth2/introspect` |
| **Authorize Endpoint** | `https://localhost:9443/oauth2/authorize` |
| JWKS URI | `https://wso2-is:9443/oauth2/jwks` |
| UserInfo Endpoint | `https://wso2-is:9443/oauth2/userinfo` |
| Scope Management Endpoint | `https://wso2-is:9443/api/identity/oauth2/v1.0/scopes` |
| DCR Endpoint | `https://wso2-is:9443/api/identity/oauth2/dcr/v1.1/register` |

> The **Authorize Endpoint** must stay on `localhost:9443` — it is the URL the browser follows. All other endpoints are server-to-server (APIM → IS inside Docker) so they use the `wso2-is` Docker hostname.

6. Scroll to **Connector Configurations**:

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin` |

7. Click **Save**

APIM registers itself in IS via DCR, automatically creating `apim_publisher` and `apim_devportal` service providers in IS.

---

## Step 3 — Configure GitHub OAuth

### 3a — Create a GitHub OAuth App

Go to `https://github.com/settings/developers` → **OAuth Apps → New OAuth App**

| Field | Value |
|-------|-------|
| Application name | `WSO2 Microservice Demo` |
| Homepage URL | `https://localhost:9443` |
| Authorization callback URL | `https://localhost:9443/commonauth` |

Click **Register application**, then click **Generate a new client secret**.

Save the **Client ID** and **Client Secret** — you need them in the next step.

### 3b — Add GitHub as a Connection in WSO2 IS

1. Go to `https://localhost:9443/console` → log in with `admin` / `admin`
2. In the left sidebar: **Connections → New Connection**
3. Search for **GitHub** and select it (built-in template)
4. Fill in:

| Field | Value |
|-------|-------|
| Name | `GitHub` |
| Client ID | *(paste from GitHub)* |
| Client Secret | *(paste from GitHub)* |
| Callback URL | `https://localhost:9443/commonauth` |

5. Click **Finish**

### 3c — Configure GitHub Attribute Mapping

After creating the connection, open it and go to the **Attributes** tab:

Map the following GitHub claims to IS attributes:

| GitHub Claim | IS Attribute |
|-------------|--------------|
| `email` | `http://wso2.org/claims/emailaddress` |
| `login` | `http://wso2.org/claims/username` |
| `name` | `http://wso2.org/claims/displayName` |
| `avatar_url` | `http://wso2.org/claims/profileUrl` |

Click **Update**.

### 3d — Enable GitHub Login on APIM Portals

APIM's portals are registered as applications in IS. Add GitHub as a login option to each.

1. Go to `https://localhost:9443/console` → **Applications**
2. Open **`apim_devportal`**:
   - Go to **Sign-in Method** tab
   - Click **Add Sign In Option** (under the existing username/password step)
   - Select **GitHub** from the list
   - Click **Update**
3. Repeat for **`apim_publisher`**

> If `apim_devportal` / `apim_publisher` are not listed, go to `https://localhost:9444/admin` → Key Managers → WSO2IS → open and re-save. This re-triggers DCR and creates the service providers.

### 3e — Allow User Registration from GitHub (Optional)

By default IS may block self-registration. To allow GitHub users to be auto-provisioned:

1. `https://localhost:9443/console` → **Login & Registration → User Onboarding → Self Registration**
2. Toggle **Enable** → **Update**

---

## Step 4 — Publish APIs

> Do this once. Config persists in `wso2-apim-db`.

Go to `https://localhost:9444/publisher` → log in with `admin` / `admin` → **Create API → Design a New REST API**

Create three APIs:

### Auth API
| Field | Value |
|-------|-------|
| Name | `AuthAPI` |
| Context | `/auth` |
| Version | `v1` |
| Backend URL | `http://auth-service:8001` |

Resources to add:
- `GET /me` — OAuth2 protected
- `POST /users/provision` — OAuth2 protected

### Product API
| Field | Value |
|-------|-------|
| Name | `ProductAPI` |
| Context | `/products` |
| Version | `v1` |
| Backend URL | `http://product-service:8002` |

Resources to add:
- `GET /` — public (no auth)
- `GET /{id}` — public
- `POST /` — OAuth2 protected
- `PUT /{id}` — OAuth2 protected
- `DELETE /{id}` — OAuth2 protected

### Order API
| Field | Value |
|-------|-------|
| Name | `OrderAPI` |
| Context | `/orders` |
| Version | `v1` |
| Backend URL | `http://order-service:8003` |

Resources to add:
- `GET /` — OAuth2 protected
- `GET /{id}` — OAuth2 protected
- `POST /` — OAuth2 protected
- `PATCH /{id}/cancel` — OAuth2 protected

For each API after adding resources:
1. **Runtime** tab → enable **JWT** under backend JWT
2. **Deploy** → select Default gateway → **Deploy**
3. **Publish**

---

## Step 5 — End-to-End Test

### Login and get a token via DevPortal

1. Go to `https://localhost:9444/devportal` → **Sign In**
2. Click **Login with GitHub** → authorize the GitHub app
3. IS provisions your GitHub account as a user
4. In DevPortal: **Applications → Add Application** → name it `TestApp` → **Save**
5. Open `TestApp` → **Production Keys** tab → **Generate Keys**
6. Click **Generate Access Token** → copy the token

### Call APIs through the gateway

```bash
TOKEN="<paste_token_here>"

# List products (public — no token needed)
curl -k http://localhost:8281/products/v1/products/

# Create a product
curl -k -X POST http://localhost:8281/products/v1/products/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Widget", "price": "9.99", "stock": 100}'

# Place an order
curl -k -X POST http://localhost:8281/orders/v1/orders/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"product_id": 1, "quantity": 2}]}'

# Get my orders
curl -k http://localhost:8281/orders/v1/orders/ \
  -H "Authorization: Bearer $TOKEN"

# Cancel an order
curl -k -X PATCH http://localhost:8281/orders/v1/orders/1/cancel \
  -H "Authorization: Bearer $TOKEN"
```

> Use `-k` to skip TLS verification for the self-signed cert. Alternatively, open `https://localhost:8244` in your browser once and click **Advanced → Proceed** to trust the cert.

---

## Persistence

Configuration and data persist in Docker named volumes:

| Volume | Contents |
|--------|----------|
| `wso2-is-db` | IS identity, user, OAuth2, and GitHub IdP config |
| `wso2-is-data` | IS tenant data |
| `wso2-apim-db` | APIM APIs, subscriptions, applications, Key Manager config |
| `wso2-apim-data` | APIM tenant data |
| `auth-db` | auth-service PostgreSQL data |
| `product-db` | product-service PostgreSQL data |
| `order-db` | order-service PostgreSQL data |

Wipe everything and start fresh:

```bash
docker compose down -v
docker compose up -d
```

Wipe only IS config (e.g. after changing IS hostname):

```bash
docker compose down wso2-is wso2-apim
docker volume rm claude-microservice-demo_wso2-is-db
docker compose up -d wso2-is
# wait for IS healthy, then:
docker compose up -d wso2-apim
```

---

## Mounted Config Files

| File | Purpose |
|------|---------|
| `wso2-is-conf/deployment.toml` | IS hostname = `localhost`; DB paths |
| `wso2-is-conf/security/wso2carbon.jks` | IS TLS cert — SAN: `wso2-is` + `localhost`, valid 10 years |
| `wso2-is-conf/security/client-truststore.jks` | IS truststore |
| `wso2-apim-conf/deployment.toml` | APIM `offset = 1` (shifts all ports +1) |
| `wso2-apim-conf/client-truststore.jks` | APIM truststore — trusts IS cert |

---

## Troubleshooting

**Config wiped after restart**
Volumes `wso2-is-db` and `wso2-apim-db` must mount to `repository/database/` inside each container. Check `docker-compose.yml`.

**Key Manager import fails with internal server error**
SSL hostname mismatch. The IS cert must have `wso2-is` as a SAN (it does if you followed this guide). If you regenerated IS from scratch, re-run the cert generation steps.

**`https://localhost:9443/console` redirects to `wso2-is:9443`**
IS `hostname` in `wso2-is-conf/deployment.toml` is set to `wso2-is`. Change it back to `localhost`, then wipe and restart the IS database volume (see Persistence section above).

**`apim_devportal` / `apim_publisher` not visible in IS Applications**
Re-save the WSO2IS Key Manager in APIM Admin to re-trigger DCR.

**GitHub login button not showing on DevPortal**
GitHub was not added as a Sign In Option on the `apim_devportal` application in IS. See Step 3d.

**Gateway returns 401 Unauthorized**
Verify `JWKS_URI` in `docker-compose.yml` points to `https://wso2-is:9443/oauth2/jwks`. Rebuild microservices: `docker compose up -d --build`.

**Self-registration blocked for GitHub users**
Enable Self Registration in IS Console → Login & Registration → User Onboarding. See Step 3e.
