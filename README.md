# identify-ip

[![PyPI - Version](https://img.shields.io/pypi/v/identify-ip.svg)](https://pypi.org/project/identify-ip)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/identify-ip.svg)](https://pypi.org/project/identify-ip)

A Python library and CLI tool for identifying IP address details — including the IP protocol version and the registered owner (registrant) via RDAP lookup.

---

## Table of Contents

- [Installation](#installation)
- [CLI Usage](#cli-usage)
- [Python Usage](#python-usage)
- [API Reference](#api-reference)
- [How It Works](#how-it-works)
- [Rate Limiting & Retries](#rate-limiting--retries)
- [License](#license)

---

## Installation

**From PyPI:**
```console
pip install identify-ip
```

**From source (latest):**
```console
pip install git+https://github.com/nathanea05/identify-ip.git
```

---

## CLI Usage

Two equivalent commands are registered: `identify-ip` and `idip`.

```console
identify-ip <IP Address> [options]
idip        <IP Address> [options]
```

### Options

| Flag | Description |
|------|-------------|
| *(none)* | Print a full summary line |
| `-r`, `--registrant` | Print only the registrant name |
| `-v`, `--version` | Print only the IP protocol version (`4` or `6`) |
| `-h`, `--help` | Show help and exit |

### Examples

```console
$ identify-ip 8.8.8.8
8.8.8.8 is an IPv4 IP Address Registered by 'Google LLC'.

$ idip 8.8.8.8 -r
Google LLC

$ idip 8.8.8.8 -v
4

$ identify-ip 2606:4700:4700::1111 -r
Cloudflare, Inc.
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Invalid IP address |

---

## Python Usage

```python
from identify_ip import get_ip_info

# Full summary string
print(get_ip_info("8.8.8.8"))
# "8.8.8.8 is an IPv4 IP Address Registered by 'Google LLC'."

# Registrant name only
print(get_ip_info("8.8.8.8", filt="registrant"))
# "Google LLC"

# IP version only
print(get_ip_info("8.8.8.8", filt="version"))
# "4"
```

---

## API Reference

### `get_ip_info(ip_str, filt="all") -> str`

The main entry point. Validates the IP, performs an RDAP lookup, and returns a formatted string.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ip_str` | `str` | The IP address to look up (IPv4 or IPv6) |
| `filt` | `"all"` \| `"registrant"` \| `"version"` | Controls what is returned |

Returns:
- `"all"` — `"<ip> is an IPv<version> IP Address Registered by '<registrant>'."`
- `"registrant"` — registrant name, or `"registrant not found for IP Address <ip>"` if unavailable
- `"version"` — `"4"` or `"6"`

Raises `ValueError` if `ip_str` is not a valid IP address.

---

### Lower-level functions

These are importable from `identify_ip.idip` but are not part of the stable public API.

#### `get_ip_registrant(ip_str) -> str | None`
Returns the registrant name for the given IP, or `None` if not found or the RDAP lookup failed.

#### `get_ip_version(ip_str) -> int`
Returns `4` or `6`. Raises `ValueError` for an invalid IP.

#### `get_rdap_data(ip_str, *, base_url=...) -> dict | None`
Returns the raw RDAP response as a parsed JSON dict, or `None` on network/HTTP failure.

---

## How It Works

1. The IP string is validated using Python's built-in `ipaddress` module.
2. An HTTP GET is sent to `https://rdap.arin.net/registry/ip/<ip>`. ARIN's bootstrap service redirects non-ARIN IPs to the correct Regional Internet Registry (RIPE, APNIC, LACNIC, AFRINIC), which `requests` follows automatically.
3. The RDAP JSON response contains nested `entities` arrays. Each entity can have a `vcardArray` (jCard format) and a list of `roles`. The parser searches depth-first for an entity with the `"registrant"` role and extracts the best available name field (`fn` → `org` → `name` → `handle`).

---

## Rate Limiting & Retries

The library is designed to be safe to call in a loop:

- **Throttle:** A minimum of 200 ms is enforced between outbound RDAP requests (module-level).
- **Automatic retries:** Uses `urllib3.Retry` — up to 6 retries with exponential backoff on HTTP 429, 500, 502, 503, and 504. Respects `Retry-After` response headers.
- **Post-retry 429 handling:** If a 429 persists after all retries and the server provides a `Retry-After` ≤ 60 seconds, the library waits once more (with a small random jitter) and retries. Otherwise it returns `None` rather than blocking indefinitely.

---

## License

`identify-ip` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

