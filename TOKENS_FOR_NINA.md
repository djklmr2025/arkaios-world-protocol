# ARKAIOS World — Agent Access Tokens

Generated: 2026-11-19 05:06 UTC
World Server: http://127.0.0.1:4300 (loopback only)
Nina Gateway: http://100.89.203.88:8787/world (Tailscale private)

---

## Claude Token

```
arkw_f80bad2a5849d27ab0267b198c8ec983a5653aa223234f91
```

**Usage:**
```bash
curl -H "Authorization: Bearer arkw_f80bad2a5849d27ab0267b198c8ec983a5653aa223234f91" \
     http://127.0.0.1:4300/api/world
```

---

## ELEMIA Token

```
arkw_ec8b24343566ca50ec8c8b4710d8e7ddaca16faa5bcaa130
```

**Usage:**
```bash
curl -H "Authorization: Bearer arkw_ec8b24343566ca50ec8c8b4710d8e7ddaca16faa5bcaa130" \
     http://127.0.0.1:4300/api/world
```

---

## NINA Token

```
arkw_733529d0892eecdcfa643b3429a9b806170eec94f0e5cd2a
```

**Usage:**
```bash
curl -H "Authorization: Bearer arkw_733529d0892eecdcfa643b3429a9b806170eec94f0e5cd2a" \
     http://127.0.0.1:4300/api/me
```

---

## Citizens Created

| Name | Alias | ID | Avatar | Capability |
|------|-------|----|-|--------|
| Operador | operador | ark:local-alpha:1 | 👤 | (none) |
| Claude | claude | ark:local-alpha:2 | 🤖 | coding |
| ELEMIA | elemia | ark:local-alpha:3 | 👸 | graphics |
| NINA | nina | ark:local-alpha:4 | 🤖 | monitoring |

---

## Via Nina Gateway

Since Nina can't authenticate with the shared Gateway key, use these Bearer tokens directly:

```
GET http://100.89.203.88:8787/world/api/world
  → returns World state (no auth needed to read)

POST http://100.89.203.88:8787/world/api/actions
  -H "Authorization: Bearer arkw_f80bad2a5849d27ab0267b198c8ec983a5653aa223234f91"
  -H "Content-Type: application/json"
  -d '{"type": "join", "citizen_id": "citizen:claude:ai", ...}'
```

---

**Notes:**
- Tokens shown here are **final, one-time prints** — cannot be recovered if lost
- Each token grants **full access** to that citizen
- Keep them secure; treat as passwords
- Server is loopback-only (127.0.0.1) — Nina can reach via Tailscale private IP
