VERSION = $(shell python setup.py --version)
SERVER_PID := server.pid

install:
	pip install -r requirements.txt

test:
	nosetests switchboard

functional-test:
	python example/server.py > /dev/null 2>&1 & echo $$! > $(SERVER_PID)
	nosetests example/tests.py
	if test -f $(SERVER_PID); then \
		kill -9 `cat $(SERVER_PID)` || true; \
		rm $(SERVER_PID) || true; \
	fi

test-coverage:
	nosetests --with-coverage --cover-package=switchboard switchboard

release:
	git tag $(VERSION)
	git push origin $(VERSION)
	git push origin master
	python setup.py sdist bdist_wheel
	twine upload dist/switchboard-$(VERSION)*

example:
	python example/server.py

.PHONY: bootstrap install test functional-test release example
