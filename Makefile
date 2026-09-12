# Borealis — build, check, test, package.  Needs `make` (dnf install make);
# without it just run the scripts directly: ./build.py && tools/check.py
.PHONY: all build check test test-light package install apply clean

all: build check

build:                 ## generate everything into build/share
	./build.py

check:                 ## syntax, QML, SVG, packages, Plymouth rules, contrast
	tools/check.py

test:                  ## screenshots from a sandboxed nested Plasma (dark)
	tools/testsession.py dark --switcher --gtk

test-light:            ## the same for the light variant
	tools/testsession.py light --switcher --gtk

package: build check   ## KDE Store archives into dist/
	tools/package.py

install: build         ## copy into ~/.local/share (changes nothing else)
	./install.sh

apply: build           ## install and switch this desktop to Borealis Dark
	./install.sh --apply dark --gtk --terminal

clean:                 ## drop build/ and dist/
	rm -rf build dist
