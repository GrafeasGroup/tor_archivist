setup:
	poetry2setup > setup.py

build: setup shiv

clean:
	rm setup.py

shiv:
	mkdir -p build
	shiv -c tor_archivist -o build/tor_archivist.pyz . --compressed
