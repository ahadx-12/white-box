import os, sys

ALLOWED_SERVICES = {"api", "worker", "dashboard"}
PORT = os.getenv("PORT", "8000")

def exec_cmd(cmd):
    os.execvp(cmd[0], cmd)

def detect_service(environ):
    raw_service = environ.get("TRUSTAI_SERVICE", "").lower().strip()
    if raw_service:
        if raw_service in ALLOWED_SERVICES:
            return raw_service
        return "api"
    if environ.get("PORT"):
        return "api"
    railway_name = environ.get("RAILWAY_SERVICE_NAME", "").lower()
    if "worker" in railway_name:
        return "worker"
    return "api"

def main() -> None:
    raw_service = os.environ.get("TRUSTAI_SERVICE", "").lower().strip()
    service = detect_service(os.environ)
    if raw_service and raw_service not in ALLOWED_SERVICES:
        print(f"Warning: TRUSTAI_SERVICE={raw_service} is invalid; defaulting to api")

    print(f"TrustAI launcher: service={service} port={PORT}")

    if service == "api":
        exec_cmd(
            [
                "uvicorn",
                "trustai_api.main:create_app",
                "--factory",
                "--app-dir",
                "apps/api/src",
                "--host",
                "0.0.0.0",
                "--port",
                PORT,
            ]
        )
    elif service == "worker":
        exec_cmd(["python", "-m", "trustai_worker.worker"])
    elif service == "dashboard":
        os.chdir("apps/dashboard")
        exec_cmd(["npm", "run", "start", "--", "-p", PORT])
    else:
        print("Set TRUSTAI_SERVICE=api|worker|dashboard")
        sys.exit(1)


if __name__ == "__main__":
    main()
