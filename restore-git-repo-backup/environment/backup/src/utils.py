"""Utility functions."""


def format_output(text):
    return f"[OUTPUT] {text}"


def parse_input(raw):
    return raw.strip().split(",")
