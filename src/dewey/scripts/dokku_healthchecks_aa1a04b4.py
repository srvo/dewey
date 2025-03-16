import subprocess

def check_port_conflicts():
    """Check for port conflicts across all Dokku apps."""
    ports_in_use = {}
    apps = subprocess.run(
        ["dokku", "apps:list"],
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    for app in apps:
        ports = subprocess.run(
            ["dokku", "proxy:ports", app],
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        for port in ports:
            if ":" in port:
                port_num = port.split(":")[1].split(" ")[0]
                if port_num in ports_in_use:
                    print(f"❌ Port conflict: {port_num} is used by both {ports_in_use[port_num]} and {app}")
                else:
                    ports_in_use[port_num] = app
                    print(f"✅ Port {port_num} is used by {app}")

if __name__ == "__main__":
    check_port_conflicts()import subprocess

def validate_container_config(app, expected_config):
    """Validate that a container's config matches the expected values."""
    config = subprocess.run(
        ["dokku", "config:show", app],
        capture_output=True,
        text=True,
    ).stdout

    for key, value in expected_config.items():
        if f"{key}={value}" not in config:
            print(f"❌ {app}: {key} is not set to {value}")
        else:
            print(f"✅ {app}: {key} is correctly set to {value}")

if __name__ == "__main__":
    expected_config = {
        "NEXT_PUBLIC_API_URL": "http://100.110.141.34:3000/api",
        "SEARX_INSTANCE": "http://100.110.141.34:3000",
    }
    validate_container_config("farfalle", expected_config)import requests

def check_service_accessibility(service, ip, port, path="/"):
    """Check if a service is accessible via its Tailscale IP."""
    url = f"http://{ip}:{port}{path}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {service} is accessible at {url}")
        else:
            print(f"⚠️ {service} returned status code {response.status_code} at {url}")
    except requests.exceptions.RequestException as e:
        print(f"❌ {service} is not accessible at {url}: {e}")

if __name__ == "__main__":
    check_service_accessibility("farfalle", "100.110.141.34", 3000, "/api/health")
    check_service_accessibility("minio", "100.110.141.34", 9000, "/minio/health/live")#!/bin/bash

apps=("farfalleminiosearxng")

for app in "${apps[@]}"; do
    echo "Running healthchecks for $app..."
    dokku checks:run "$app"
    if [ $? -eq 0 ]; then
        echo "✅ $app healthchecks passed"
    else
        echo "❌ $app healthchecks failed"
    fi
doneimport subprocess

def analyze_logs(app):
    """Analyze logs for errors or warnings."""
    logs = subprocess.run(
        ["dokku", "logs", app],
        capture_output=True,
        text=True,
    ).stdout

    errors = ["error", "fail", "warn"]
    for line in logs.splitlines():
        if any(error in line.lower() for error in errors):
            print(f"⚠️ {app}: {line}")

if __name__ == "__main__":
    analyze_logs("farfalle")
    analyze_logs("minio")import subprocess

def verify_tailscale_ips(app, expected_ip):
    """Verify that a service is using the correct Tailscale IP."""
    config = subprocess.run(
        ["dokku", "config:show", app],
        capture_output=True,
        text=True,
    ).stdout

    if expected_ip not in config:
        print(f"❌ {app} is not configured with Tailscale IP {expected_ip}")
    else:
        print(f"✅ {app} is correctly configured with Tailscale IP {expected_ip}")

if __name__ == "__main__":
    verify_tailscale_ips("farfalle", "100.110.141.34")
    verify_tailscale_ips("minio", "100.110.141.34")import os

def validate_env_vars(app, required_vars):
    """Validate that all required environment variables are set."""
    for var in required_vars:
        if var not in os.environ:
            print(f"❌ {app}: {var} is not set")
        else:
            print(f"✅ {app}: {var} is set")

if __name__ == "__main__":
    required_vars = ["OPENAI_API_KEY", "DEEPSEEK_API_KEY"]
    validate_env_vars("farfalle", required_vars)
