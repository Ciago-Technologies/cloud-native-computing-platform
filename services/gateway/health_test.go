package gateway

import "testing"

func TestHealthy(t *testing.T) {
	if !Healthy() {
		t.Fatal("gateway scaffold should be healthy")
	}
}
