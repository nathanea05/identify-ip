# CLAUDE.md — identify-ip

## Before Making Any Changes

Always explain your **reasoning**, **assumptions**, and **implementation plan** before touching any code. This means:

1. State what the current behavior is and why it's a problem (or what the goal is).
2. List any assumptions you're making about inputs, callers, or existing behavior.
3. Describe specifically what you will change and why — before writing a single line.

Do not skip this even for small changes. It surfaces misunderstandings early.

---

## Project Overview

`identify-ip` is a Python library and CLI tool for looking up information about IP addresses. It has two capabilities:

- **IP version detection** — uses the stdlib `ipaddress` module to determine IPv4 vs IPv6.
- **Registrant lookup** — queries RDAP (Registration Data Access Protocol) to find the organization or person who registered the IP address.

**Use case:** Programmatically identify the ISP or owner of an IP address, e.g. identifying the carrier for each WAN interface in a large network.

---

## Repository Layout

```
src/identify_ip/
    __init__.py     # Public API: exports get_ip_info only
    __about__.py    # Version string (read by hatch)
    idip.py         # All logic: RDAP client, parsers, CLI entrypoint
tests/
    __init__.py     # Empty; tests not yet written
pyproject.toml      # hatch build system, dependencies, CLI scripts
```

---

## Public API

### Python

```python
from identify_ip import get_ip_info

# Returns a formatted string based on the filter
get_ip_info(ip_str, filt="all")        # "1.2.3.4 is an IPv4 IP Address Registered by 'Acme Corp'."
get_ip_info(ip_str, filt="registrant") # "Acme Corp"  (or "registrant not found for IP Address ...")
get_ip_info(ip_str, filt="version")    # "4"
```

Only `get_ip_info` is exported from the package. Lower-level functions (`get_rdap_data`, `get_ip_registrant`, `get_ip_version`, `parse_entities`) live in `idip.py` and are importable directly but are not part of the stable public surface.

### CLI

```
identify-ip [options] <IP>
idip        [options] <IP>

  (no flags)   Full summary line
  -r           Registrant name only
  -v           IP version only
```

Exit codes: `0` = success, `1` = invalid IP.

---

## RDAP Client Details

- **Base URL:** `https://rdap.arin.net/registry/ip/` (ARIN bootstrap — ARIN redirects non-ARIN IPs to the correct RIR)
- **Throttle:** 200 ms minimum between calls (module-level `_throttle()`)
- **Retries:** urllib3 `Retry` — up to 6 retries on 429/500/502/503/504 with exponential backoff (`backoff_factor=0.8`), respects `Retry-After`
- **Post-retry 429 handling:** If still 429 after retries and `Retry-After` ≤ 60 s, sleeps once more with jitter then retries; otherwise returns `None`
- **Timeout:** 15 s per request
- **Session:** module-level singleton `_SESSION`

---

## RDAP Parsing

RDAP responses nest registrant data inside `entities` arrays, each containing a `vcardArray` (jCard format). The parser:

1. `parse_vcard_array` — converts jCard list to `{name: value}` dict
2. `get_vcard_name` — extracts the best available name: `fn` → `org` → `name` → `handle`
3. `parse_entities` — depth-first search preferring entities with `"registrant"` role

---

## Dependencies

- `requests>=2.31` (runtime)
- `hatchling` (build only)
- Python `>=3.8`

---

## Known Limitations / Watch-Outs

- Only `get_ip_info` is in `__all__`; adding new public functions requires updating `__init__.py`.
- No tests exist yet beyond an empty `tests/__init__.py`.
- The ARIN base URL is hardcoded; ARIN will issue HTTP redirects for IPs registered with other RIRs (RIPE, APNIC, etc.), which `requests` follows automatically.
- RDAP HTTP errors are swallowed inside `get_rdap_data` (returns `None`); callers receive "registrant not found" rather than an error. There is no way to distinguish a network failure from a genuinely unregistered IP at the `get_ip_info` level.
