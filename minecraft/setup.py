"""Install the real-game environment: a JDK, the official Minecraft server and the bridge.

    python -m minecraft.setup

Everything goes to $PISTON_DOOR_HOME (default ~/.cache/piston-door-take-home), nothing into the
repository. Three steps, each skipped when already done:

1. Java 25 (what Minecraft 26.3 asks for): $PISTON_DOOR_JAVA if set, else a JDK found on PATH
   or in JAVA_HOME, else Eclipse Temurin downloaded from adoptium.net.
2. The 26.3 server from Mojang (checked against the SHA-1 in Mojang's own version manifest),
   unpacked into server.jar plus its libraries.
3. The bridge (minecraft/bridge, plain Java) compiled against them with javac.

By downloading the server you accept the Minecraft EULA (https://aka.ms/MinecraftEULA).
"""
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "26.3"
MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
JAVA_MAJOR = 25
BRIDGE = Path(__file__).resolve().parent / "bridge"
MAIN_CLASS = "dev.vjeux.mctas.bridge.Main"


def home():
    return Path(os.environ.get("PISTON_DOOR_HOME") or Path.home() / ".cache" / "piston-door-take-home")


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "piston-door-take-home"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def _exe(name):
    return name + (".exe" if os.name == "nt" else "")


def _java_major(java):
    try:
        out = subprocess.run([str(java), "-version"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = out.stderr + out.stdout
    for token in text.replace('"', " ").split():
        head = token.split(".")[0]
        if head.isdigit() and int(head) >= 8:
            return int(head)
    return None


def find_java():
    """Path of a `java` binary of at least JAVA_MAJOR that has `javac` next to it, or None."""
    candidates = []
    if os.environ.get("PISTON_DOOR_JAVA"):
        candidates.append(Path(os.environ["PISTON_DOOR_JAVA"]))
    jdks = home() / "jdk"
    if jdks.is_dir():
        candidates += sorted(jdks.glob("**/bin/" + _exe("java")), reverse=True)
    if os.environ.get("JAVA_HOME"):
        candidates.append(Path(os.environ["JAVA_HOME"]) / "bin" / _exe("java"))
    on_path = shutil.which("java")
    if on_path:
        candidates.append(Path(on_path).resolve())
    for java in candidates:
        if java.exists() and (java.parent / _exe("javac")).exists() and (_java_major(java) or 0) >= JAVA_MAJOR:
            return java
    return None


def install_java():
    java = find_java()
    if java:
        return java
    system = {"Windows": "windows", "Darwin": "mac", "Linux": "linux"}[platform.system()]
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "aarch64", "aarch64": "aarch64"}[platform.machine().lower()]
    url = f"https://api.adoptium.net/v3/binary/latest/{JAVA_MAJOR}/ga/{system}/{arch}/jdk/hotspot/normal/eclipse"
    print(f"downloading Eclipse Temurin {JAVA_MAJOR} ({system} {arch})", flush=True)
    data = _fetch(url)
    dest = home() / "jdk"
    dest.mkdir(parents=True, exist_ok=True)
    if system == "windows":
        zipfile.ZipFile(io.BytesIO(data)).extractall(dest)
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            tar.extractall(dest)
    java = find_java()
    if not java:
        raise RuntimeError(f"no usable JDK {JAVA_MAJOR} after download; set PISTON_DOOR_JAVA to a java binary")
    return java


def install_server():
    """Download and unpack the server. Returns (server.jar, libs directory)."""
    root = home() / VERSION
    server_jar, libs = root / "server.jar", root / "libs"
    stamp = root / ".server-installed"
    if stamp.exists() and server_jar.exists():
        return server_jar, libs
    manifest = json.loads(_fetch(MANIFEST))
    entry = next(v for v in manifest["versions"] if v["id"] == VERSION)
    meta = json.loads(_fetch(entry["url"]))
    server = meta["downloads"]["server"]
    print(f"downloading the Minecraft {VERSION} server ({server['size'] // 1_000_000} MB)", flush=True)
    bundle = _fetch(server["url"])
    if hashlib.sha1(bundle).hexdigest() != server["sha1"]:
        raise RuntimeError("the server download does not match Mojang's SHA-1")
    libs.mkdir(parents=True, exist_ok=True)
    # Since 1.18 the download is a launcher that carries the real jar and its libraries.
    with zipfile.ZipFile(io.BytesIO(bundle)) as z:
        for listing, prefix, is_server in (("META-INF/versions.list", "META-INF/versions/", True),
                                           ("META-INF/libraries.list", "META-INF/libraries/", False)):
            for line in z.read(listing).decode().splitlines():
                cols = line.split("\t")
                if len(cols) < 3:
                    continue
                data = z.read(prefix + cols[2])
                if hashlib.sha256(data).hexdigest() != cols[0]:
                    raise RuntimeError(f"checksum mismatch for {cols[2]} in the server bundle")
                (server_jar if is_server else libs / Path(cols[2]).name).write_bytes(data)
    stamp.write_text("ok")
    return server_jar, libs


def classpath(classes, server_jar, libs):
    return os.pathsep.join([str(classes), str(server_jar), str(libs / "*")])


def build_bridge(java, server_jar, libs):
    """Compile minecraft/bridge. Cached by a hash of its sources."""
    sources = sorted(BRIDGE.rglob("*.java"))
    digest = hashlib.sha256(b"".join(p.read_bytes() for p in sources)).hexdigest()[:12]
    out = home() / VERSION / f"bridge-{digest}"
    classes = out / "classes"
    if (out / ".built").exists():
        return classes
    print(f"compiling the bridge ({len(sources)} files)", flush=True)
    tmp = out.with_name(out.name + f".tmp-{os.getpid()}")
    shutil.rmtree(tmp, ignore_errors=True)
    (tmp / "classes").mkdir(parents=True)
    run = subprocess.run(
        [str(java.parent / _exe("javac")), "--release", str(JAVA_MAJOR), "-nowarn", "-encoding", "UTF-8",
         "-cp", os.pathsep.join([str(server_jar), str(libs / "*")]), "-d", str(tmp / "classes"), *map(str, sources)],
        capture_output=True, text=True)
    if run.returncode:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError("javac failed:\n" + run.stdout + run.stderr)
    shutil.copy(BRIDGE / "mctas-log4j2.xml", tmp / "mctas-log4j2.xml")
    (tmp / ".built").write_text("ok")
    shutil.rmtree(out, ignore_errors=True)
    tmp.rename(out)
    return classes


def install():
    """Run every step and return what a worker needs to start."""
    java = install_java()
    server_jar, libs = install_server()
    classes = build_bridge(java, server_jar, libs)
    return {"java": str(java), "classpath": classpath(classes, server_jar, libs),
            "log4j": str(classes.parent / "mctas-log4j2.xml"), "home": str(home())}


def installed():
    """The same as install() when everything is already there, else None. Downloads nothing."""
    java = find_java()
    root = home() / VERSION
    if not java or not (root / ".server-installed").exists():
        return None
    return install()


if __name__ == "__main__":
    cfg = install()
    print(f"ready: Minecraft {VERSION}, java {cfg['java']}, files in {cfg['home']}")
    sys.exit(0)
