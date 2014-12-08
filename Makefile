VERSION = $(shell python setup.py --version)

install:
	pip install -r requirements.txt

sysdeps:
	if which apt-get &> /dev/null; then \
		sudo apt-get install -y libmemcached
	elif which brew &> /dev/null; then \
		brew install libmemcached
	fi

test:
	nosetests

release:
	git tag $(VERSION)
	git push origin $(VERSION)
	git push origin master
	python setup.py sdist upload

.PHONY: install sysdeps test release
