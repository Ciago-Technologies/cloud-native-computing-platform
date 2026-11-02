.PHONY: test test-python test-rust test-go

test:
	$(MAKE) test-python
	$(MAKE) test-rust
	$(MAKE) test-go

test-python:
	python3 -m unittest discover -s tests -v

test-rust:
	cargo test --workspace

test-go:
	go test ./...
