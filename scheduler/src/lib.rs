pub fn prefers_local_execution(local_capable: bool) -> bool {
    local_capable
}

#[cfg(test)]
mod tests {
    use super::prefers_local_execution;

    #[test]
    fn prefers_local_execution_when_capable() {
        assert!(prefers_local_execution(true));
        assert!(!prefers_local_execution(false));
    }
}
