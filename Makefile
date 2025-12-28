.PHONY: build test_upload upload

build:
	uv build

test_upload:
	twine upload -r testpypi dist/*

upload:
	twine upload dist/*
