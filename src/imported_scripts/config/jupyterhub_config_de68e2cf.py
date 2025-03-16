import os
from jupyterhub.auth import DummyAuthenticator

# Basic Configuration
c.JupyterHub.bind_url = 'http://:8000'
c.ConfigurableHTTPProxy.should_start = True

# Security Settings
c.ConfigurableHTTPProxy.auth_token = os.environ.get('CONFIGPROXY_AUTH_TOKEN', '')
c.JupyterHub.cookie_secret = os.environ.get('COOKIE_SECRET', '')

# Authentication Settings
c.JupyterHub.authenticator_class = DummyAuthenticator
c.DummyAuthenticator.password = os.environ.get('JUPYTER_PASSWORD', '')
c.Authenticator.admin_users = {'sloane@ethicic.com'}
c.Authenticator.allowed_users = {'sloane@ethicic.com'}

# Storage and Environment
c.Spawner.notebook_dir = '/storage/jupyterhub'
c.Spawner.default_url = '/lab'

# Docker settings
c.JupyterHub.trusted_downstream_ips = ['172.17.0.1', '127.0.0.1']

# Proxy and Network settings
c.JupyterHub.cleanup_servers = True
c.JupyterHub.cleanup_proxy = True
c.ConfigurableHTTPProxy.api_url = 'http://127.0.0.1:8001'
c.ConfigurableHTTPProxy.command = ['configurable-http-proxy']

# Security hardening
c.JupyterHub.ssl_enabled = False
c.JupyterHub.allow_root = False
c.Spawner.disable_user_config = True
c.Spawner.mem_limit = '1G'

# Make sure directory exists and has right permissions
if not os.path.exists('/storage/jupyterhub'):
    os.makedirs('/storage/jupyterhub', exist_ok=True)
    os.chmod('/storage/jupyterhub', 0o770)