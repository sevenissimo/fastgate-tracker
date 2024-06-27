#!/bin/bash

HOST:=192.168.1.254
USER:=admin
PASS:=secret_pswd

# XSRF Token (unused)
#token=$(hexdump -vn16 -e'4/4 "%08X" 1 "\n"' /dev/urandom) # Random hex string
#token=$(printf '%31s' 0 | tr \  0)                        # Zero filled string
token="0"                                                  # Just a not-empty string

# Cookie Jar
cookies=$(mktemp); trap 'rm -rf -- "$cookies"' EXIT

# Login (cmd=3)
session=$(
  curl -s -G \
      -c "$cookies" \
      -d "cmd=3" \
      -d "nvget=login_confirm" \
      -d "username=$USER" \
      -d "password=$PASS" \
      -H "X-XSRF-TOKEN: $token" \
    "http://${HOST}/status.cgi" \
  | jq -r '.login_confirm.check_session')

# HTTP/1.0 200 OK
# Set-Cookie: XSRF-TOKEN=0308B2A2913Fxxxxxxxxxxxxxxxxx; sameSite
# Content-type: text/json

# {
#   "login_confirm": {
#     "check_session": "x6jaShA+nW0wmt1xCXIxxxxxxxxxxxxxxxxxxxxxxxx",
#     "check_user": "1",
#     "check_pwd": "1",
#     "login_confirm": "end"
#   }
# }

# {
#   "login_confirm": {
#     "login_status": "0"
#   }
# }

# Set Token to received one (unused)
#token=$(awk '/XSRF-TOKEN/ {print $NF}' "$cookies") # Not needed

# Debug
#echo "sessionKey=$session"
#echo "X-XSRF-TOKEN=$token"

devices=$(
  curl -s -G \
      -b "$cookies" \
      -d "nvget=connected_device_list" \
      --data-urlencode "sessionKey=$session" \
    "http://${HOST}/status.cgi" \
  | jq -r '.connected_device_list[]')


echo "$devices"
