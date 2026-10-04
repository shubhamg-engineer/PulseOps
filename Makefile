.PHONY: setup data train run test clean all

PYTHON := python

setup:
	$(PYTHON) -m pip install -r requirements.txt

data:
	$(PYTHON) -m src.data_generator
	$(PYTHON) -m src.validate_data

train:
	$(PYTHON) -m src.model

run:
	streamlit run app/streamlit_app.py

test:
	pytest -v tests/

clean:
	rm -rf data/*.parquet data/*.csv data/*.duckdb data/*.json data/*.joblib
