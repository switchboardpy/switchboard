VERSION = $(shell python setup.py --version)

install:
	pip install -r requirements.txt

test:
	nosetests

release:
	git tag $(VERSION)
	git push origin $(VERSION)
	git push origin master
	python setup.py sdist upload

.PHONY: install test release
