init:
	pip install -r requirements.txt

test:
	nosetests tests

swing:
	python -m bin.swing

check:
	python -m bin.check

plot:
	python -m bin.plot

explore:
	python -m bin.explore
