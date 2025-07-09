#!/usr/bin/env python3
"""Check if a port is available and suggest alternatives if not."""
import sys
import socket


def is_port_available(port):
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            return True
    except OSError:
        return False


def find_available_port(start_port, max_attempts=10):
    """Find an available port starting from start_port."""
    for i in range(max_attempts):
        port = start_port + i
        if is_port_available(port):
            return port
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_port.py <port>", file=sys.stderr)
        sys.exit(2)
    
    try:
        preferred_port = int(sys.argv[1])
    except ValueError:
        print(f"Invalid port: {sys.argv[1]}", file=sys.stderr)
        sys.exit(2)
    
    if is_port_available(preferred_port):
        # Port is available
        sys.exit(0)
    else:
        # Find alternative port
        alt_port = find_available_port(preferred_port + 1)
        if alt_port:
            print(alt_port)
            sys.exit(1)
        else:
            # No alternative found
            sys.exit(2)


if __name__ == "__main__":
    main()