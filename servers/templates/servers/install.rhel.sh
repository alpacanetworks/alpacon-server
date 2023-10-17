#!/bin/bash

yum install -y python3

curl -sSLf -o /tmp/{{ package_name }} {{ package_url }}
pip3 install -U /tmp/{{ package_name }}
rm -f /tmp/{{ package_name }}

export ALPACON_URL="{{ alpacon_url }}"
export ALPAMON_ID="{{ alpamon_id }}"
export ALPAMON_KEY="{{ alpamon_key }}"

alpamon-deploy install
