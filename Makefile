init:
	pip install -r requirements.txt

test:
	nosetests tests


circle:
	python -m bin.circle $(exchange) $(targets)

circle-explore:
	python -m bin.circle_explore $(exchange) $(targets)

circle-check:
	python -m bin.circle_check

circle-test:
	python -m bin.circle_test


swing:
	python -m bin.swing $(exchange) $(bridges)

swing-explore:
	python -m bin.swing_explore $(exchange) $(bridges)

swing-plot:
	python -m bin.swing_plot

swing-check:
	python -m bin.swing_check
