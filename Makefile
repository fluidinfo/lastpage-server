.PHONY: test deploy run clean wc pep8 pyflakes lint

test:
	trial lastpage

deploy: all
	fab live deploy

run:
	twistd -n lastpage --serve-static-files

clean:
	rm -f lastpage-[0-9]*-[0-9]*-server.tar.bz2
	find . -name '*~' -o -name '*.pyc' -print0 | xargs -0 -r rm

wc:
	find lastpage twisted -name '*.py' -print0 | xargs -0 wc -l

pep8:
	find lastpage twisted -name '*.py' -print0 | xargs -0 -n 1 pep8 --repeat

pyflakes:
	find lastpage twisted -name '*.py' -print0 | xargs -0 pyflakes

lint: pep8 pyflakes
