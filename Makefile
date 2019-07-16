init:
	pip install -r requirements.txt

test:
	nosetests tests

runbot:
	python -m bin.runbot
