venv:
	py -3.10 -m venv .venv
	.venv/Scripts/pip.exe install matplotlib pandas

bench:
	.venv/Scripts/python.exe pipeline.py

