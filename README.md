# identify-ip

[![PyPI - Version](https://img.shields.io/pypi/v/identify-ip.svg)](https://pypi.org/project/identify-ip)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/identify-ip.svg)](https://pypi.org/project/identify-ip)

-----

## Table of Contents

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install git+ssh://git@github.com/nathanea05/identify-ip.git
```

## License

`identify-ip` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.


## About
`identify-ip` is a simple program used to identify details about an IP address. It uses the builtin ipaddress Python library
to detect IP Protocol Version, Type, and other details, and will query the appropriate RDAP server to detect the name of the
Registrant.

This is helpful in situations where you need to programatically detect the owner of an IP Address. For example, if you are
managing a large network and need a way to detect the ISP for each WAN connection within that network, you can pass the WAN
IP address into identify-ip with the "registrant" filter, and it will return the name of the Company/User who registered that
IP address.

## Command Line Usage
identify-ip [options] <IP Address>

idip [options] <IP Address>

Options:
-h: Display the help menu
-v: Print the IP Protocol Version
-r: Print the RDAP Registrant

## Python Usage
from identify-ip import get_ip_info

registrant = get_ip_info("8.8.8.8", filt="registrant")

