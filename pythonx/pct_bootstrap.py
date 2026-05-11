import importlib.util
import os
import shutil
import subprocess
import sys


DEPS = ["peewee"]


def _venv(root):
	return os.path.join(root, ".venv")


def _venv_python(root):
	if os.name == "nt":
		return os.path.join(_venv(root), "Scripts", "python.exe")
	return os.path.join(_venv(root), "bin", "python")


def add_venv_to_path(root):
	paths = [os.path.join(_venv(root), "Lib", "site-packages")]
	lib = os.path.join(_venv(root), "lib")
	if os.path.isdir(lib):
		paths += [os.path.join(lib, name, "site-packages") for name in os.listdir(lib) if name.startswith("python")]

	added = []
	for path in paths:
		if os.path.isdir(path) and path not in sys.path:
			sys.path.insert(0, path)
			added.append(path)
	return added


def _missing(names):
	return [name for name in names if importlib.util.find_spec(name) is None]


def health(root, host_is_nvim=False):
	add_venv_to_path(root)
	messages = []
	missing = _missing(DEPS)
	if missing:
		messages += [
			"ERROR missing runtime deps: {}".format(", ".join(missing)),
			"INFO run :PctBootstrap",
		]
	else:
		messages.append("OK runtime deps available: {}".format(", ".join(DEPS)))

	if not os.path.exists(_venv_python(root)):
		messages.append("WARN local venv missing: {}".format(_venv(root)))

	if host_is_nvim and _missing(["pynvim"]):
		messages.append("WARN pynvim missing in current Neovim provider")

	return not missing, messages


def _run(args, cwd):
	proc = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	return proc.returncode, proc.stdout.strip()


def bootstrap(root, host_is_nvim=False):
	messages = []
	python = _venv_python(root)
	uv = shutil.which("uv")

	if not os.path.exists(python):
		cmd = [uv, "venv", _venv(root)] if uv else [sys.executable, "-m", "venv", _venv(root)]
		code, output = _run(cmd, root)
		messages.append("INFO " + " ".join(cmd))
		if output:
			messages.append(output)
		if code != 0:
			return False, messages + ["ERROR failed to create local venv"]

	cmd = [uv, "pip", "install", "--python", python] + DEPS if uv else [python, "-m", "pip", "install"] + DEPS
	code, output = _run(cmd, root)
	messages.append("INFO " + " ".join(cmd))
	if output:
		messages.append(output)
	if code != 0:
		return False, messages + ["ERROR failed to install runtime deps"]

	ok, health_messages = health(root, host_is_nvim)
	return ok, messages + health_messages
