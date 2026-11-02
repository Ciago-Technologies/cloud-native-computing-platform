pub fn runtime_name() -> &'static str {
    "rust-desktop-runtime"
}

#[cfg(test)]
mod tests {
    use super::runtime_name;

    #[test]
    fn identifies_the_native_runtime() {
        assert_eq!(runtime_name(), "rust-desktop-runtime");
    }
}
