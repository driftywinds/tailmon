## Tailmon - Notifications for your Tailscale Mesh

<img align="left" width="100" height="100" src="https://i.postimg.cc/zGbww7hz/id-U5z-X3036-1759758123436.jpg"> Apprise notifications for devices in your Tailscale Mesh going online or offline

<br>

[![Pulls](https://img.shields.io/docker/pulls/driftywinds/tailmon.svg?style=for-the-badge)](https://img.shields.io/docker/pulls/driftywinds/tailmon.svg?style=for-the-badge)

Everytime a device comes online or goes offline in your Tailscale mesh, you will get a notification in the specified Apprise endpoints.

Also available on Docker Hub - [```driftywinds/tailmon:latest```](https://hub.docker.com/repository/docker/driftywinds/tailmon/general)

### How to use: - 

1. Download the ```compose.yml``` and ```.env``` files from the repo [here](https://github.com/driftywinds/rssrise).
2. Go to [https://login.tailscale.com/admin/settings/keys](https://login.tailscale.com/admin/settings/keys) and generate a API token for your account.
3. Customise the ```.env``` file according to your needs, fill the API token and mesh name.
4. Run ```docker compose up -d```.

<br>

You can check logs live with this command: - 
```
docker compose logs -f
```
### For dev testing: -
- have python3 installed on your machine
- clone the repo
- go into the directory and run these commands: -
```
python3 -m venv .venv
source .venv/bin/activate
pip install --no-cache-dir -r requirements.txt
```  
- configure ```.env``` variables.
- then run ```python3 main.py```
