# serde-dataclass Changelog

### v0.0.4 (2026-04-04)

- Fixed a bug where setting custom deserializer would override the cast hooks, causing type checking to fail. Now both custom deserializer and cast hooks work together seamlessly.

### v0.0.3 (2026-04-04)

- JSON decoding now correctly parses lists to tuples and passes type check.

### v0.0.1 (2026-03-26)

- Initial release
