"""Build OPERATION: IRON LINE into a single executable.

    python build.py              a windowed build, which is what ships
    python build.py --console    the same thing with a console behind it

The second one exists because a windowed build that dies before the
window opens dies INVISIBLY - no traceback, no message, just a process
that was there and then was not. If the release build will not start,
build the console one and run it from a terminal.

Everything here is one file and no assets, so there is nothing to copy
in and nothing to check for. The build is the whole distribution.
"""
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "IronLine"


def main():
    console = "--console" in sys.argv
    os.chdir(HERE)
    try:
        import PyInstaller                                   # noqa: F401
    except ImportError:
        print("PyInstaller is not installed:\n"
              "    python -m pip install pyinstaller")
        return 1

    # A stale build/ is the usual reason a change does not appear in the
    # exe, so it goes before every build rather than when somebody
    # remembers.
    for d in ("build", "dist"):
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm"]
    if console:
        # the spec pins console=False, so a console build cannot use it
        cmd += ["--onefile", "--console", "--name", NAME + "Console",
                "--exclude-module", "tkinter", "iron_line.py"]
    else:
        cmd += ["iron_line.spec"]

    print("$ " + " ".join(cmd))
    t0 = time.time()
    r = subprocess.run(cmd)
    if r.returncode:
        print(f"\nBUILD FAILED ({r.returncode})")
        return r.returncode

    out = os.path.join("dist", (NAME + "Console" if console else NAME)
                       + (".exe" if os.name == "nt" else ""))
    if not os.path.isfile(out):
        print(f"\nBUILD REPORTED SUCCESS BUT {out} IS NOT THERE")
        return 1
    mb = os.path.getsize(out) / (1024 * 1024)
    print(f"\n{out}  -  {mb:.1f} MB, built in {time.time() - t0:.0f}s")
    print("\nThat file IS the distribution: no data files, no folder to "
          "ship beside it.\nThe player's profile goes to the OS data "
          "directory, never next to the exe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
