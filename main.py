import os, sys

SERVICE = os.getenv("TRUSTAI_SERVICE", "").lower()
PORT = os.getenv("PORT", "8000")

def exec_cmd(cmd):
    os.execvp(cmd[0], cmd)

if SERVICE == "api":
    exec_cmd([
        "uvicorn",
        "trustai_api.main:create_app",
        "--factory",
        "--app-dir", "apps/api/src",
        "--host", "0.0.0.0",
        "--port", PORT,
    ])
elif SERVICE == "worker":
    exec_cmd(["python", "-m", "trustai_worker.worker"])
elif SERVICE == "dashboard":
    os.chdir("apps/dashboard")
    exec_cmd(["npm", "run", "start", "--", "-p", PORT])
else:
    print("Set TRUSTAI_SERVICE=api|worker|dashboard")
    sys.exit(1)
