.PHONY: deploy run run-oauth clean wc pep8 pyflakes lint

lint: pep8 pyflakes

deploy: all
	fab live deploy

run:
	python `type twistd | cut -f3 -d' '` -n lastpage --conf conf/local.conf

run-oauth:
	python `type twistd | cut -f3 -d' '` --pidfile local-oauth.pid -n local-oauth --conf conf/local.conf

clean:
	rm -f lastpage-[0-9]*-[0-9]*-server.tar.bz2
	find . -name '*~' -o -name '*.pyc' -print0 | xargs -0 -r rm

wc:
	find lastpage twisted -name '*.py' -print0 | xargs -0 wc -l

pep8:
	find lastpage twisted -name '*.py' -print0 | xargs -0 -n 1 pep8 --repeat

pyflakes:
	find lastpage twisted -name '*.py' -print0 | xargs -0 pyflakes
