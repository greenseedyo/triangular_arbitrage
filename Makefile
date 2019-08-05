init:
	pip install -r requirements.txt

test:
	nosetests tests

circle:
	python -m bin.circle

circle-check:
	python -m bin.circle_check

swing:
	python -m bin.swing

check:
	python -m bin.check

plot:
	python -m bin.plot

explore:
	python -m bin.explore
