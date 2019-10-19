init:
	pip install -r requirements.txt

test:
	nosetests tests

circle:
	python -m bin.circle $(exchange) $(targets)

circle-check:
	python -m bin.circle_check

circle-explore:
	python -m bin.circle_explore

circle-test:
	python -m bin.circle_test

swing:
	python -m bin.swing $(exchange) $(bridges)

check:
	python -m bin.check

plot:
	python -m bin.plot

explore:
	python -m bin.explore
