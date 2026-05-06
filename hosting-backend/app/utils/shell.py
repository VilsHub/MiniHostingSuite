def run(cmd: str):
    import subprocess
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)