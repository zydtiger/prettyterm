.PHONY: build clean test_upload upload

build:
	uv build

clean:
	rm -rf dist

test_upload:
	twine upload -r testpypi dist/*

upload:
	twine upload dist/*
