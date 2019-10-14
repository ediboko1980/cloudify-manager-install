#!/bin/bash
set -eux
ip=$(/usr/sbin/ip a s | /usr/bin/grep -oE 'inet [^/]+' | /usr/bin/cut -d' ' -f2 | /usr/bin/grep -v '^127.' | /usr/bin/grep -v '^169.254.' | /usr/bin/head -n1)
cfy_manager configure --verbose --private-ip $ip --public-ip $ip
cfy_manager start --verbose
